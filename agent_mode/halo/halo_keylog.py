"""
Halo MCC key press logger — captures Ken's live inputs while he
plays so ken-ai can learn from imitation instead of just parallel
observation.

Long-running daemon. Launched via spawn (not spawnSync) and kept
alive until /api/halo/keylog/stop POSTs a SIGTERM. Streams every
key + mouse event as a JSONL line to halo-keylog.jsonl under the
ken-ai-latest memory dir.

The `keyboard` module's global hooks receive ALL system key
events (monitoring is global even though input injection is
foreground-only). That's exactly what we need here: observe
Ken's presses regardless of which window has focus.

Entry shape:
    {"at": ISO, "kind": "key", "key": "w", "dir": "down"}
    {"at": ISO, "kind": "key", "key": "space", "dir": "up"}
    {"at": ISO, "kind": "mouse", "button": "left", "dir": "down"}

Note: pure keyboard events are reliable. Mouse events via the
`mouse` module sometimes miss high-rate moves in games; we log
button clicks only, not continuous mouse motion.

Usage:
    python halo_keylog.py                  # runs forever until SIGINT/SIGTERM
    python halo_keylog.py --stop-after 60  # auto-exit after N seconds
"""

import sys
import json
import time
import signal
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    import keyboard as _kb
except Exception as e:
    sys.stderr.write("keyboard module required: " + str(e) + "\n")
    sys.exit(2)

try:
    import mouse as _ms
    HAS_MS = True
except Exception:
    _ms = None
    HAS_MS = False


def _log_path():
    # Resolve memories/ken-ai-latest relative to this script.
    here = Path(__file__).resolve().parent
    log = here.parent / "memories" / "ken-ai-latest" / "halo-keylog.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    return log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-after", type=int, default=0,
                        help="auto-exit after N seconds (0 = forever)")
    parser.add_argument("--skip-mouse", action="store_true",
                        help="only log keyboard, not mouse buttons")
    args = parser.parse_args()

    log_path = _log_path()
    # Line-buffered so each event hits disk immediately — the
    # Node observer tails this file every tick and needs fresh
    # data, not a 4KB buffered chunk.
    fh = open(log_path, "a", buffering=1, encoding="utf-8")
    _running = {"v": True}

    def write_event(evt):
        try:
            evt["at"] = datetime.now(timezone.utc).isoformat()
            fh.write(json.dumps(evt) + "\n")
        except Exception:
            pass

    def on_key(evt):
        # evt is a keyboard.KeyboardEvent with .name, .event_type
        try:
            write_event({
                "kind": "key",
                "key": evt.name or "?",
                "dir": evt.event_type,  # 'down' or 'up'
                "scan_code": getattr(evt, "scan_code", None),
            })
        except Exception:
            pass

    def on_mouse(evt):
        try:
            # evt is a mouse.ButtonEvent or MoveEvent or WheelEvent.
            # We only keep buttons — movement is too noisy to log
            # and the game loop already captures camera deltas via
            # screenshots.
            etype = evt.__class__.__name__
            if etype == "ButtonEvent":
                write_event({
                    "kind": "mouse",
                    "button": evt.button,
                    "dir": evt.event_type,  # 'down' or 'up'
                })
        except Exception:
            pass

    _kb.hook(on_key)
    if HAS_MS and not args.skip_mouse:
        _ms.hook(on_mouse)

    def shutdown(*_a):
        _running["v"] = False
        try: _kb.unhook_all()
        except Exception: pass
        if HAS_MS and not args.skip_mouse:
            try: _ms.unhook_all()
            except Exception: pass
        try: fh.close()
        except Exception: pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except Exception:
        pass

    # Announce start so the Node side knows the daemon is live.
    write_event({"kind": "system", "msg": "keylog started",
                 "skip_mouse": args.skip_mouse, "pid": None})
    sys.stdout.write(json.dumps({"ok": True, "log": str(log_path)}) + "\n")
    sys.stdout.flush()

    start = time.time()
    while _running["v"]:
        time.sleep(0.25)
        if args.stop_after and (time.time() - start) >= args.stop_after:
            break
    shutdown()


if __name__ == "__main__":
    main()
