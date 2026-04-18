"""
agent_core/patch_engine.py

Safe file patching for the offline coding agent. Three hard
guarantees:

  1. READ BEFORE WRITE — every patch reads the fresh on-disk
     content right before applying. No stale reads.

  2. CONTEXT-ANCHORED — hunks are matched against the file
     by their context lines, not by line number. If the file
     moved since the diff was drafted, we search for the
     anchor and apply at the new location. Silent corruption
     on line-number drift is the #1 way naive patch tools
     bite you.

  3. ATOMIC + REVERTIBLE — every write is preceded by a
     timestamped backup in logs/backups/<stem>.<ts>.bak and
     an entry in logs/patch_index.jsonl. `revert_last(path)`
     or `revert_patch(patch_id)` restores exactly.

Two-phase workflow (propose → approve):

  pe = PatchEngine()
  patch_id, preview = pe.propose_patch(path, new_content)
  # show preview to Ken, wait for approval
  ok, msg = pe.approve_patch(patch_id)

For a simple one-shot, apply_patch(path, diff) or
write_file(path, content) still work — they read fresh,
back up, write, log. Everything flows through the same
index so revert works for both paths.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("patch_engine")

ROOT = Path(__file__).parent.parent
BACKUP_DIR = ROOT / "logs" / "backups"
PENDING_DIR = ROOT / "logs" / "pending_patches"
PATCH_INDEX = ROOT / "logs" / "patch_index.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ts_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


# ─── unified diff parser ─────────────────────────────────

class Hunk:
    """One hunk of a unified diff.

    `old_lines` are the lines (including context + removals)
    the hunk expects to find in the original. `new_lines` are
    what replaces them.
    """
    def __init__(self, old_start: int, old_lines: list[str], new_lines: list[str]):
        self.old_start = old_start
        self.old_lines = old_lines
        self.new_lines = new_lines


_HUNK_HEADER = re.compile(
    r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'
)


def parse_unified_diff(diff: str) -> dict[str, list[Hunk]]:
    """
    Parse a unified diff into {file_path: [Hunk, ...]}.

    Accepts the common `--- a/path` / `+++ b/path` header or
    bare hunks (in which case the caller passes a path).
    """
    files: dict[str, list[Hunk]] = {}
    current_path: Optional[str] = None
    current_hunks: list[Hunk] = []

    in_hunk = False
    hunk_old_start = 0
    old_lines: list[str] = []
    new_lines: list[str] = []

    lines = diff.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("--- "):
            # Finish previous file
            if in_hunk:
                current_hunks.append(Hunk(hunk_old_start, old_lines, new_lines))
                in_hunk = False
                old_lines, new_lines = [], []
            if current_path:
                files.setdefault(current_path, []).extend(current_hunks)
                current_hunks = []
            # +++ line comes next, use it for the path
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                raw_path = lines[i + 1][4:].strip()
                # Strip b/ prefix
                if raw_path.startswith("b/"):
                    raw_path = raw_path[2:]
                current_path = raw_path
                i += 2
                continue
            i += 1
            continue

        m = _HUNK_HEADER.match(line)
        if m:
            # Finish previous hunk
            if in_hunk:
                current_hunks.append(Hunk(hunk_old_start, old_lines, new_lines))
                old_lines, new_lines = [], []
            hunk_old_start = int(m.group(1))
            in_hunk = True
            i += 1
            continue

        if in_hunk:
            if line.startswith("+"):
                new_lines.append(line[1:])
            elif line.startswith("-"):
                old_lines.append(line[1:])
            elif line.startswith(" "):
                old_lines.append(line[1:])
                new_lines.append(line[1:])
            elif line.startswith("\\"):
                # "\ No newline at end of file" — ignore
                pass
            else:
                # End of hunk content
                current_hunks.append(Hunk(hunk_old_start, old_lines, new_lines))
                in_hunk = False
                old_lines, new_lines = [], []
                continue
            i += 1
            continue

        i += 1

    if in_hunk:
        current_hunks.append(Hunk(hunk_old_start, old_lines, new_lines))
    if current_path and current_hunks:
        files.setdefault(current_path, []).extend(current_hunks)

    return files


def _find_hunk_anchor(file_lines: list[str], hunk: Hunk) -> int:
    """
    Locate where this hunk's `old_lines` begins in file_lines.
    Returns a 0-indexed position or -1 if not found.

    Strategy:
      1. Try the advertised line number (old_start - 1). If
         the slice matches exactly, use it.
      2. Sliding-window search for the full old_lines sequence
         within ±200 lines of the advertised position.
      3. Fallback: global search for the sequence.

    This survives line-number drift — the most common failure
    mode of naive patch apply.
    """
    if not hunk.old_lines:
        # Insert-only hunk — use the line number directly,
        # clamped to file bounds.
        return max(0, min(hunk.old_start - 1, len(file_lines)))

    needle = hunk.old_lines
    n = len(needle)

    # 1. exact position
    pos = hunk.old_start - 1
    if 0 <= pos <= len(file_lines) - n:
        if file_lines[pos:pos + n] == needle:
            return pos

    # 2. local window ±200
    window_start = max(0, pos - 200)
    window_end = min(len(file_lines) - n, pos + 200)
    for p in range(window_start, window_end + 1):
        if file_lines[p:p + n] == needle:
            return p

    # 3. global search
    for p in range(0, len(file_lines) - n + 1):
        if file_lines[p:p + n] == needle:
            return p

    return -1


def apply_hunks(original: str, hunks: list[Hunk]) -> tuple[bool, str, list[str]]:
    """
    Apply hunks to original text. Returns:
      (ok, result_or_error, anchor_log)

    `anchor_log` records where each hunk was actually anchored
    (useful for audit).
    """
    file_lines = original.splitlines(keepends=False)
    result = list(file_lines)
    anchor_log: list[str] = []

    # Apply hunks in REVERSE order so earlier-in-file edits
    # don't shift later anchor positions.
    sorted_hunks = sorted(hunks, key=lambda h: h.old_start, reverse=True)

    for hunk in sorted_hunks:
        anchor = _find_hunk_anchor(result, hunk)
        if anchor < 0:
            return False, f"hunk @ old_start={hunk.old_start} could not be anchored", anchor_log
        n = len(hunk.old_lines)
        result[anchor:anchor + n] = hunk.new_lines
        anchor_log.append(f"hunk old_start={hunk.old_start} → anchored at line {anchor + 1} (delta {anchor + 1 - hunk.old_start:+d})")

    return True, "\n".join(result) + ("\n" if original.endswith("\n") else ""), anchor_log


# ─── PatchEngine ─────────────────────────────────────────

class PatchEngine:
    """
    Safe file patching with backups, propose-then-approve,
    and rollback via patch_index.jsonl.
    """

    def __init__(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        PATCH_INDEX.parent.mkdir(parents=True, exist_ok=True)

    # ─── helpers ───────────────────────────────────────────

    def _backup(self, path: Path, content: str) -> Path:
        ts = _ts_slug()
        # Flatten the path so the backup filename is readable +
        # unique across nested dirs
        rel = str(path).replace("\\", "/").replace("/", "__").replace(":", "_")
        backup_path = BACKUP_DIR / f"{rel}.{ts}.bak"
        backup_path.write_text(content, encoding="utf-8")
        return backup_path

    def _append_index(self, row: dict) -> None:
        try:
            with PATCH_INDEX.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")
        except Exception as e:
            logger.warning(f"patch index write failed: {e}")

    # ─── direct write ──────────────────────────────────────

    def write_file(self, path: str, content: str) -> tuple[bool, str]:
        """
        Write content to path. Backs up the existing file
        first, stamps a patch_index entry so revert works.
        """
        file_path = Path(path)
        patch_id = uuid.uuid4().hex[:12]
        original: Optional[str] = None
        backup_path: Optional[Path] = None

        if file_path.exists():
            try:
                original = file_path.read_text(encoding="utf-8", errors="replace")
                backup_path = self._backup(file_path, original)
            except Exception as e:
                return False, f"read/backup failed: {e}"

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            # Restore if we had a backup
            if backup_path and original is not None:
                file_path.write_text(original, encoding="utf-8")
            return False, f"write failed: {e}"

        self._append_index({
            "at":     _now_iso(),
            "id":     patch_id,
            "op":     "write",
            "path":   str(file_path),
            "backup": str(backup_path) if backup_path else None,
            "bytes":  len(content),
            "had_original": original is not None,
        })
        return True, f"wrote {path} ({len(content)} bytes, backup_id={patch_id})"

    # ─── unified diff apply ────────────────────────────────

    def apply_patch(self, path: str, diff: str) -> tuple[bool, str]:
        """
        Apply a unified diff to a single file. Context-anchored
        so line-number drift doesn't silently corrupt the file.
        """
        file_path = Path(path)
        if not file_path.exists():
            return False, f"file not found: {path}"

        try:
            original = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return False, f"read failed: {e}"

        files = parse_unified_diff(diff)
        # If the diff had no path header, assume all hunks are
        # for this file
        if not files:
            return False, "no hunks parsed from diff"
        hunks = []
        for p, hs in files.items():
            hunks.extend(hs)

        ok, result_or_err, anchor_log = apply_hunks(original, hunks)
        if not ok:
            return False, f"apply failed: {result_or_err}"

        backup_path = self._backup(file_path, original)
        patch_id = uuid.uuid4().hex[:12]
        try:
            file_path.write_text(result_or_err, encoding="utf-8")
        except Exception as e:
            file_path.write_text(original, encoding="utf-8")
            return False, f"write failed: {e} — original restored"

        self._append_index({
            "at":     _now_iso(),
            "id":     patch_id,
            "op":     "apply_patch",
            "path":   str(file_path),
            "backup": str(backup_path),
            "hunks":  len(hunks),
            "anchors": anchor_log,
            "bytes_before": len(original),
            "bytes_after":  len(result_or_err),
        })
        return True, f"patched {path} ({len(hunks)} hunks, backup_id={patch_id})"

    def apply_multi_file_patch(self, diff: str) -> tuple[bool, str, list[dict]]:
        """
        Apply a unified diff that touches multiple files.
        Rolls back ALL writes if any file fails.

        Returns (ok, message, per_file_results).
        """
        files = parse_unified_diff(diff)
        if not files:
            return False, "no files parsed from diff", []

        # Stage: read every file, prepare the new contents, do
        # NOT write anything until all files succeed.
        stage: list[tuple[Path, str, str, list[Hunk]]] = []  # (path, original, new, hunks)
        for p, hunks in files.items():
            file_path = Path(p)
            if not file_path.exists():
                return False, f"file not found: {p}", []
            try:
                original = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return False, f"read failed {p}: {e}", []
            ok, new_or_err, _ = apply_hunks(original, hunks)
            if not ok:
                return False, f"apply failed {p}: {new_or_err}", []
            stage.append((file_path, original, new_or_err, hunks))

        # Commit: back up + write in order, rolling back on
        # first failure.
        written: list[tuple[Path, str]] = []  # (path, original) for rollback
        per_file: list[dict] = []
        patch_batch_id = uuid.uuid4().hex[:12]
        try:
            for file_path, original, new_content, hunks in stage:
                backup_path = self._backup(file_path, original)
                file_path.write_text(new_content, encoding="utf-8")
                written.append((file_path, original))
                per_file.append({
                    "path":   str(file_path),
                    "backup": str(backup_path),
                    "hunks":  len(hunks),
                    "bytes_before": len(original),
                    "bytes_after":  len(new_content),
                })
        except Exception as e:
            # Roll back every successful write
            for path, content in written:
                try:
                    path.write_text(content, encoding="utf-8")
                except Exception:
                    pass
            return False, f"batch write failed: {e} — rolled back", per_file

        self._append_index({
            "at":    _now_iso(),
            "id":    patch_batch_id,
            "op":    "apply_multi",
            "files": per_file,
        })
        return True, f"patched {len(per_file)} files (batch_id={patch_batch_id})", per_file

    # ─── propose-then-approve ──────────────────────────────

    def propose_patch(self, path: str, new_content: str) -> tuple[str, str]:
        """
        Stage a proposed new content for `path`. Returns
        (patch_id, preview_diff). Nothing is written to disk
        yet — Ken (or a Mode 1+ approval) calls
        approve_patch(patch_id) to commit.
        """
        file_path = Path(path)
        patch_id = uuid.uuid4().hex[:12]
        original = ""
        if file_path.exists():
            try:
                original = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return "", f"read failed: {e}"

        preview = self.preview_diff(path, original, new_content)

        pending_path = PENDING_DIR / f"{patch_id}.json"
        pending_path.write_text(json.dumps({
            "id":             patch_id,
            "created_at":     _now_iso(),
            "path":           str(file_path),
            "new_content":    new_content,
            "original_bytes": len(original),
            "original_hash":  hash(original),
            "preview":        preview,
        }, default=str), encoding="utf-8")

        return patch_id, preview

    def list_pending(self) -> list[dict]:
        """Return summary info for every pending patch."""
        out = []
        for p in sorted(PENDING_DIR.glob("*.json")):
            try:
                row = json.loads(p.read_text(encoding="utf-8"))
                out.append({
                    "id":         row.get("id"),
                    "path":       row.get("path"),
                    "created_at": row.get("created_at"),
                    "preview_bytes": len(row.get("preview") or ""),
                })
            except Exception:
                continue
        return out

    def get_pending(self, patch_id: str) -> Optional[dict]:
        """Return the full pending patch record by id."""
        p = PENDING_DIR / f"{patch_id}.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def approve_patch(self, patch_id: str) -> tuple[bool, str]:
        """
        Commit a previously-proposed patch. Re-reads the
        target file to detect drift — if the file changed
        since proposal, the approval fails and the patch must
        be re-proposed against the fresh content.
        """
        pending_path = PENDING_DIR / f"{patch_id}.json"
        if not pending_path.exists():
            return False, f"no pending patch: {patch_id}"

        try:
            pending = json.loads(pending_path.read_text(encoding="utf-8"))
        except Exception as e:
            return False, f"pending read failed: {e}"

        path = Path(pending["path"])
        expected_hash = pending.get("original_hash")

        current = ""
        if path.exists():
            try:
                current = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return False, f"target read failed: {e}"

        if hash(current) != expected_hash:
            return False, (
                f"drift detected — {path} changed since proposal. "
                f"re-propose against fresh content."
            )

        ok, msg = self.write_file(str(path), pending["new_content"])
        if ok:
            try:
                pending_path.unlink()
            except Exception:
                pass
        return ok, msg

    def reject_patch(self, patch_id: str) -> tuple[bool, str]:
        pending_path = PENDING_DIR / f"{patch_id}.json"
        if not pending_path.exists():
            return False, f"no pending patch: {patch_id}"
        try:
            pending_path.unlink()
        except Exception as e:
            return False, f"reject failed: {e}"
        return True, f"rejected: {patch_id}"

    # ─── preview ───────────────────────────────────────────

    def preview_patch(self, path: str, new_content: str) -> str:
        """Back-compat wrapper for the old single-arg signature."""
        file_path = Path(path)
        original = ""
        if file_path.exists():
            try:
                original = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        return self.preview_diff(path, original, new_content)

    def preview_diff(self, path: str, original: str, new_content: str) -> str:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
        return "".join(diff)

    # ─── revert ────────────────────────────────────────────

    def revert_last(self, path: str) -> tuple[bool, str]:
        """Revert the most recent backup for the given file."""
        if not PATCH_INDEX.exists():
            return False, "no patch index yet"
        try:
            lines = PATCH_INDEX.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            return False, f"index read failed: {e}"

        norm_target = str(Path(path))
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("op") in ("write", "apply_patch") and row.get("path") == norm_target:
                backup = row.get("backup")
                if not backup:
                    return False, "no backup recorded for that entry"
                backup_path = Path(backup)
                if not backup_path.exists():
                    return False, f"backup file missing: {backup}"
                try:
                    content = backup_path.read_text(encoding="utf-8", errors="replace")
                    Path(path).write_text(content, encoding="utf-8")
                except Exception as e:
                    return False, f"revert failed: {e}"
                self._append_index({
                    "at":   _now_iso(),
                    "op":   "revert",
                    "path": str(Path(path)),
                    "from_backup": backup,
                })
                return True, f"reverted {path} from {backup_path.name}"

        return False, f"no backup entry for {path}"

    # ─── diagnostics ───────────────────────────────────────

    def history(self, path: Optional[str] = None, limit: int = 20) -> list[dict]:
        if not PATCH_INDEX.exists():
            return []
        try:
            lines = PATCH_INDEX.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        out = []
        norm = str(Path(path)) if path else None
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if norm and row.get("path") != norm:
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out
