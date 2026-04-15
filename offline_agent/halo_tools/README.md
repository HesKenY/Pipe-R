# halo_tools — Ken's Halo MCC learning + tool rig

Absorbed from `C:\Users\Ken\Desktop\*` on 2026-04-14. Previously
lived as a scatter of bat files + python scripts on Ken's
Desktop — brought into KenAI so the brain can index them,
track usage, and feed the corpus.

## Layout

```
halo_tools/
├─ scripts/
│  ├─ ken_aimbot.py        standalone blob-detect aimbot (pyautogui)
│  ├─ halo_hunt.py         Cheat Engine-style delta memory scanner
│  └─ halo_vision_hunt.py  vision-assisted memory scanner (llama3.2-vision)
└─ launchers/
   ├─ KEN_AIMBOT_ON.bat    start aimbot (pythonw, no console)
   ├─ KEN_AIMBOT_OFF.bat   drop stop flag to halt the loop
   ├─ KEN_AIMBOT_STATS.bat read aimbot.log.jsonl, print session stats
   ├─ HALO_HUNT.bat        launch delta scanner (self-elevates to admin)
   ├─ HALO_VISION_HUNT.bat launch vision-assisted hunter (admin)
   ├─ KEN_AI_HALO_ON.bat   kick the Pipe-R halo agent stack
   ├─ KEN_AI_HALO_OFF.bat  stop the Pipe-R halo agent stack
   └─ KEN_AI_HALO_CONTROL.bat open the control panel TUI
```

Logs from live runs land in
`brain/corpus/halo_tools_logs/aimbot.log.jsonl` and
`brain/corpus/halo_tools_logs/hunt_results.jsonl`. The brain
indexer picks them up on the next rebuild and they feed the
training corpus.

## What each script does

### ken_aimbot.py
Standalone blob-detecting aimbot. Screenshots center 42% of
screen, flood-fills for red/bright_red/purple/orange palette
hits, picks biggest blob by proximity + confidence, aims at
top 4% of bbox (head bias), snaps with ctypes mouse_event,
fires burst. F10 pauses, drop `AIMBOT_STOP.flag` to halt.

Config constants at the top of the file — `CENTER_FRAC`,
`HEAD_BIAS_FRAC`, `BURST_SIZE`, `MIN_CONFIDENCE`, etc. Ken's
aggressive profile: `CENTER_FRAC=0.42, HEAD_BIAS=0.04, BURST=5,
MIN_CONFIDENCE=0.015, SCAN_INTERVAL_MS=60`.

Every scan + engagement appends a JSONL row to `aimbot.log.jsonl`
(`kind: scan|engage|heartbeat|start|error|...`). Log is capped
at 50k lines via `maybe_trim_log()`.

### halo_hunt.py
Cheat Engine-style delta scanner. Attaches to MCC, collects
every 4-byte float in [0.0, 200.0] range on first pass, then
narrows candidates on "increased / decreased / changed /
unchanged" commands as Ken plays. Goal: find the health/shield
float address, then `w 9999` to pin god mode.

Commands: `i` (initial), `d` (decreased), `u` (unchanged),
`c` (changed), `s` (show), `w N` (write), `x` (export), `q`.

Requires PROCESS_VM_READ + WRITE + OPERATION — self-elevates
to admin via PowerShell on launch.

### halo_vision_hunt.py
Vision-assisted variant. Instead of blind delta scan, asks
`llama3.2-vision` to READ the shield/health value from Halo's
HUD directly, then scans memory for that exact float. Three
rounds usually narrows candidates to < 20. `p N` starts an
80ms pin thread writing N to every candidate continuously —
that's the god-mode pin loop.

Workflow: `r` → take damage → `r` → repeat → `p 9999`. `q` to
quit.

## Integration with the rest of KenAI

- **brain index**: `brain/brain_index/halo_tools.md` has a
  bullet-list summary of every script + launcher + what they
  read/write. FTS hits on "aimbot", "halo hunt", "shield
  address" etc. return that doc.
- **corpus**: `brain/corpus/halo_tools_logs/*.jsonl` feed the
  training pipeline. `brain_build.py` picks them up on the
  next refresh.
- **Pipe-R agent_mode/halo**: the three "KEN AI HALO" launchers
  hand off to `../../agent_mode/halo/ken_ai_halo_control.py`
  which runs the live-loop stack (keylog + aim + analyzer +
  tuner + patcher + vision).

## Gotchas

- bat files in `launchers/` all `cd /d "%~dp0..\scripts"` so
  `pythonw <script>` resolves correctly. Don't flat-copy a
  launcher into a different dir without fixing that.
- `ken_aimbot.py` writes `aimbot.log.jsonl` relative to the
  script's cwd — which is `halo_tools/scripts/` after the
  launcher's cd. To import fresh logs into the brain corpus,
  run `brain/brain_build.py --once` after a session.
- `halo_vision_hunt.py` needs `pyautogui + PIL + llama3.2-vision
  pulled in ollama`. Its `vision_read_hud()` helper spawns
  `ollama run llama3.2-vision` per frame — ~5-15s latency.
- UAC self-elevation in `HALO_HUNT.bat` / `HALO_VISION_HUNT.bat`
  pops a Windows dialog — expected, accept.
