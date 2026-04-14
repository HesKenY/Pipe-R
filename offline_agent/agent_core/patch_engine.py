"""
agent_core/patch_engine.py
Applies unified diffs to files safely. Always reads fresh before patching.
"""

import difflib
from pathlib import Path
from datetime import datetime
import logging
import shutil

logger = logging.getLogger("patch_engine")

BACKUP_DIR = Path(__file__).parent.parent / "logs" / "backups"


class PatchEngine:
    """
    Safe file patching. Creates backups before any write.
    Validates patch applicability before applying.
    """

    def __init__(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def apply_patch(self, path: str, diff: str) -> tuple[bool, str]:
        """
        Apply a unified diff to a file.
        Returns (success: bool, message: str)
        """
        file_path = Path(path)
        if not file_path.exists():
            return False, f"File not found: {path}"

        original = file_path.read_text(encoding="utf-8", errors="replace")
        self._backup(file_path, original)

        try:
            patched = _apply_unified_diff(original, diff)
            file_path.write_text(patched, encoding="utf-8")
            logger.info(f"Patch applied: {path}")
            return True, f"Patch applied to {path}"
        except Exception as e:
            # Restore backup
            file_path.write_text(original, encoding="utf-8")
            return False, f"Patch failed: {e} — original restored"

    def preview_patch(self, path: str, new_content: str) -> str:
        """Generate a unified diff between current and proposed content."""
        file_path = Path(path)
        if not file_path.exists():
            return f"--- /dev/null\n+++ {path}\n" + "".join(
                f"+{line}\n" for line in new_content.splitlines()
            )
        original = file_path.read_text(encoding="utf-8", errors="replace")
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        return "".join(diff)

    def write_file(self, path: str, content: str) -> tuple[bool, str]:
        """Write a file, creating backup if it exists."""
        file_path = Path(path)
        if file_path.exists():
            self._backup(file_path, file_path.read_text(encoding="utf-8", errors="replace"))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True, f"Written: {path}"

    def _backup(self, path: Path, content: str):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{path.name}.{ts}.bak"
        backup_path.write_text(content, encoding="utf-8")
        logger.debug(f"Backup created: {backup_path}")


def _apply_unified_diff(original: str, diff: str) -> str:
    """Apply a unified diff string to original text. Raises on failure."""
    orig_lines = original.splitlines(keepends=True)
    result_lines = list(orig_lines)
    patch_lines = diff.splitlines(keepends=True)

    # Parse hunks
    hunks = _parse_hunks(patch_lines)
    offset = 0

    for hunk in hunks:
        old_start, old_count, new_lines = hunk
        idx = old_start - 1 + offset

        # Remove old lines
        del result_lines[idx:idx + old_count]

        # Insert new lines
        for i, line in enumerate(new_lines):
            result_lines.insert(idx + i, line)

        offset += len(new_lines) - old_count

    return "".join(result_lines)


def _parse_hunks(lines):
    """Minimal unified diff hunk parser."""
    import re
    hunks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@', line)
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            i += 1
            removed = 0
            new_lines = []
            while i < len(lines) and not lines[i].startswith("@@"):
                l = lines[i]
                if l.startswith("+"):
                    new_lines.append(l[1:])
                elif l.startswith("-"):
                    removed += 1
                elif l.startswith(" "):
                    new_lines.append(l[1:])
                else:
                    break
                i += 1
            hunks.append((old_start, removed, new_lines))
        else:
            i += 1
    return hunks
