"""
tools/death_watcher.py

Background task that tails brain/sessions/<date>/halo_events.jsonl
and triggers a full training pipeline run every time a new
`death` event appears.

Training pipeline (sequential):
  1. brain/brain_build.py --once      (pull fresh corpus)
  2. brain/model_designer.py full <slug>
  3. brain/modelfile_builder.py <slug>

Debounced: multiple deaths within TRAINING_COOLDOWN_S are
collapsed into a single training run. Only one training run
is in flight at a time (module-level lock).

Each training run:
  - appends a row to brain/corpus/death_trainings.jsonl
  - stamps a line in today's session_log.md
  - if it produced a Modelfile, the path is recorded

Runs as an asyncio task spawned from main.py's lifespan
on_startup when /api/halo/training/watch/start is called.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.win_subprocess import run as _win_run

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
BRAIN = PROJECT_ROOT / "brain"
SESSIONS = BRAIN / "sessions"
TRAININGS_LOG = BRAIN / "corpus" / "death_trainings.jsonl"

# Debounce — collapse bursts of deaths into one training run
TRAINING_COOLDOWN_S = 120

# How often to poll the halo_events.jsonl for new rows
POLL_INTERVAL_S = 3.0


class DeathWatcher:
    def __init__(self, design_slug: str = "ken-ai-offline-v0"):
        self.design_slug = design_slug
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._training_lock = asyncio.Lock()
        self._last_seen_mtime: dict[str, float] = {}
        self._seen_event_count: dict[str, int] = {}
        self._last_training_at: float = 0.0
        self._training_count: int = 0
        self._deaths_seen: int = 0
        self._last_event: Optional[dict] = None
        self._last_result: Optional[dict] = None
        self._started_at: Optional[str] = None

    # ─── lifecycle ─────────────────────────────────────────

    def start(self) -> dict:
        if self.running:
            return {"ok": False, "error": "already running"}
        self.running = True
        self._started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._task = asyncio.create_task(self._loop())
        return {"ok": True, "started_at": self._started_at, "slug": self.design_slug}

    def stop(self) -> dict:
        if not self.running:
            return {"ok": False, "error": "not running"}
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        return {"ok": True, "training_count": self._training_count, "deaths_seen": self._deaths_seen}

    def status(self) -> dict:
        return {
            "running":         self.running,
            "started_at":      self._started_at,
            "design_slug":     self.design_slug,
            "deaths_seen":     self._deaths_seen,
            "training_count":  self._training_count,
            "last_training_at": self._last_training_at,
            "last_event":      self._last_event,
            "last_result":     self._last_result,
            "training_in_progress": self._training_lock.locked(),
            "cooldown_s":      TRAINING_COOLDOWN_S,
        }

    # ─── polling loop ──────────────────────────────────────

    async def _loop(self) -> None:
        # First pass: skip any deaths already on disk so we
        # only train on NEW events after the watcher started.
        self._seed_baseline_counts()

        try:
            while self.running:
                try:
                    self._scan_once()
                except Exception as e:
                    print(f"[death_watcher] scan error: {e}")
                await asyncio.sleep(POLL_INTERVAL_S)
        except asyncio.CancelledError:
            pass

    def _seed_baseline_counts(self) -> None:
        for path in self._event_files():
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                deaths = sum(1 for l in text.splitlines() if '"kind": "death"' in l or '"kind":"death"' in l)
                self._seen_event_count[str(path)] = deaths
                self._last_seen_mtime[str(path)] = path.stat().st_mtime
            except Exception:
                self._seen_event_count[str(path)] = 0

    def _event_files(self) -> list[Path]:
        """Return every halo_events.jsonl across session dirs."""
        out = []
        if not SESSIONS.is_dir():
            return out
        for day_dir in SESSIONS.iterdir():
            if not day_dir.is_dir():
                continue
            f = day_dir / "halo_events.jsonl"
            if f.exists():
                out.append(f)
        return out

    def _scan_once(self) -> None:
        for path in self._event_files():
            key = str(path)
            mtime = path.stat().st_mtime
            if mtime == self._last_seen_mtime.get(key):
                continue
            self._last_seen_mtime[key] = mtime
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            lines = [l for l in text.splitlines() if l.strip()]
            current_deaths = sum(1 for l in lines if '"kind": "death"' in l or '"kind":"death"' in l)
            prev_deaths = self._seen_event_count.get(key, 0)
            if current_deaths > prev_deaths:
                # New death(s)! Collapse the burst into one training.
                delta = current_deaths - prev_deaths
                self._deaths_seen += delta
                # Capture the newest death row for the status payload
                for l in reversed(lines):
                    if '"kind"' in l and 'death' in l:
                        try:
                            self._last_event = json.loads(l)
                        except Exception:
                            pass
                        break
                # Cooldown check
                now = time.time()
                if now - self._last_training_at < TRAINING_COOLDOWN_S:
                    remaining = int(TRAINING_COOLDOWN_S - (now - self._last_training_at))
                    print(f"[death_watcher] +{delta} death(s), cooldown {remaining}s — skip")
                    self._seen_event_count[key] = current_deaths
                    continue
                if self._training_lock.locked():
                    print(f"[death_watcher] +{delta} death(s), training already in flight — skip")
                    self._seen_event_count[key] = current_deaths
                    continue
                self._seen_event_count[key] = current_deaths
                asyncio.create_task(self._run_training(delta))

    # ─── training pipeline ─────────────────────────────────

    async def _run_training(self, triggering_deaths: int) -> None:
        async with self._training_lock:
            self._last_training_at = time.time()
            started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[death_watcher] training triggered by {triggering_deaths} death(s)")

            result = {
                "at":                started_at,
                "triggering_deaths": triggering_deaths,
                "slug":              self.design_slug,
                "steps":             [],
            }

            loop = asyncio.get_running_loop()

            def _step(name: str, args: list[str], timeout: int = 300) -> dict:
                t0 = time.time()
                try:
                    r = _win_run(
                        args,
                        cwd=str(PROJECT_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    return {
                        "step":      name,
                        "ok":        r.returncode == 0,
                        "elapsed_s": round(time.time() - t0, 1),
                        "stdout":    (r.stdout or "")[:800],
                        "stderr":    (r.stderr or "")[:400],
                    }
                except Exception as e:
                    return {"step": name, "ok": False, "error": str(e)}

            # 1. brain refresh (pull fresh corpus)
            r1 = await loop.run_in_executor(None, _step, "brain_build",
                ["python", "brain/brain_build.py", "--once"], 120)
            result["steps"].append(r1)
            if not r1.get("ok"):
                result["ok"] = False
                self._finalize(result)
                return

            # 2. model designer full
            r2 = await loop.run_in_executor(None, _step, "model_designer_full",
                ["python", "brain/model_designer.py", "full", self.design_slug], 300)
            result["steps"].append(r2)
            if not r2.get("ok"):
                result["ok"] = False
                self._finalize(result)
                return

            # 3. modelfile builder
            model_name = f"{self.design_slug.replace('-', '')}v1"
            r3 = await loop.run_in_executor(None, _step, "modelfile_builder",
                ["python", "brain/modelfile_builder.py", self.design_slug,
                 "--name", model_name], 120)
            result["steps"].append(r3)

            result["ok"] = all(s.get("ok") for s in result["steps"])
            result["ended_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            result["model_name"] = model_name
            self._finalize(result)

    def _finalize(self, result: dict) -> None:
        self._training_count += 1
        self._last_result = result

        # Append to death_trainings.jsonl
        try:
            TRAININGS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with TRAININGS_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result, default=str) + "\n")
        except Exception as e:
            print(f"[death_watcher] log write failed: {e}")

        # Stamp session log
        try:
            day_dir = SESSIONS / datetime.now().strftime("%Y-%m-%d")
            day_dir.mkdir(parents=True, exist_ok=True)
            log_path = day_dir / "session_log.md"
            status = "OK" if result.get("ok") else "FAIL"
            elapsed = sum(s.get("elapsed_s", 0) for s in result.get("steps", []))
            line = (
                f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                f"**DEATH-TRAIN {status}** "
                f"— triggered by {result.get('triggering_deaths',0)} death(s), "
                f"{elapsed:.0f}s total\n"
            )
            with log_path.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[death_watcher] session log append failed: {e}")

        print(f"[death_watcher] training {self._training_count} done: ok={result.get('ok')}")


# Module-level singleton so main.py can reach it from endpoints
_watcher: Optional[DeathWatcher] = None


def get_watcher() -> DeathWatcher:
    global _watcher
    if _watcher is None:
        _watcher = DeathWatcher()
    return _watcher


def start(slug: str = "ken-ai-offline-v0") -> dict:
    w = get_watcher()
    if slug and slug != w.design_slug:
        w.design_slug = slug
    return w.start()


def stop() -> dict:
    return get_watcher().stop()


def status() -> dict:
    return get_watcher().status()
