# Memory Index

## Core Repo
- `hub.js` - terminal command deck and project launcher
- `server.js` - HTTP API for the remote dashboard and web UI
- `pipe-r.html` - main sci-fi browser UI
- `remote.html` - mobile remote control UI

## Working Folders
- `input/` - source projects dropped in for work
- `output/` - deliverables and packaged builds
- `workspace/` - active in-progress work
- `staging/` - review-ready artifacts

## Agent / Training System
- `agent_mode/` - orchestration, dispatch, logging, registry
- `agents/` - agent state and helper scripts
- `datasets/` - training datasets and imports

## Logging Convention
- Runtime logs now live in `.claude/logs/`
- Session checkpoints should live in `.claude/SESSION_LOG.md`
- Repo memory / navigation notes belong in `.claude/MEMORY_INDEX.md`

## Current Halo Training Shape
- `agent_mode/halo/agent.js` now has async Ollama inference for the main drive/observe decision call; this was done to reduce server freezes while Halo training is live.
- `agent_mode/halo/training_mode.js` persists `safety_net`, `target_practice`, and `one_hit_kill` in `agent_mode/config/halo_training.json`.
- Active Halo learning artifacts live under `agent_mode/memories/ken-ai-latest/`:
  - `halo-keylog.jsonl` - Ken's real inputs for imitation
  - `halo-log.jsonl` - autonomous drive-loop decisions
  - `halo-events.jsonl` - extracted combat/learning events
  - `halo-memory.md` - distilled lessons used in later prompts
- Current live training recipe in Codex: training mode ON, keylog ON, analyzer ON, vision ON, trainer ON, Halo loop in drive mode, aimbot engage ON with single-shot target-practice reps.
- Desktop Halo control surface now lives at `agent_mode/halo/ken_ai_halo_control.py`; desktop launchers are `C:\Users\Ken\Desktop\Ken AI Halo Control.bat`, `KEN AI HALO ON.bat`, and `KEN AI HALO OFF.bat`.
- Overlay reads `halo-log.jsonl`, `halo-keylog.jsonl`, `halo-events.jsonl`, `halo_training.json`, and persisted `halo-vision-cache.json` to show what Ken AI is doing/seeing even when the server is under load.
- `agent_mode/halo/jumpstart.js` now builds `agent_mode/memories/ken-ai-latest/halo-jumpstart.json` from keylogs/events/halo ticks and exposes `jumpstartPromptBlock()` for live prompts.
- Overlay/control app now reads jumpstart data so the Halo overlay shows Ken-style movement/combat priors, not just raw keys and vision.
- Latest jumpstart profile from live logs: heavy `d`/`w` bias, frequent `strafe_shoot`, grenade openings, and noob-combo reps.

## BRAIN-first deck iteration
- `brain/` is now the first-rule repository for the new deck build.
- `brain/BRAIN.db` is the master local index for logs, memories, dreams, branch state, plans, and model-design docs.
- `brain/repositories.json` controls which roots BRAIN is allowed to ingest.
- Current approved roots:
  - `codex` -> `C:\Users\Ken\Desktop\Codex`
  - `claude_import` -> `C:\Users\Ken\Desktop\Codex\input\Claude-import`
- `brain/BRAIN_CHARTER.md` defines the operating rule: BRAIN Controller + Ken AI Chat are the two core deck-native control surfaces.
- `brain/MODEL_DESIGNER_SPEC.md` defines the target proprietary model capability envelope:
  - local-first execution
  - full workstation file visibility
  - vision context
  - tool execution
  - shell execution
  - memory logging
  - dream synthesis
  - branch-aware planning
- `server.js` now exposes `/api/brain/status`, `/api/brain/rebuild`, `/api/brain/search`, `/api/brain/context`, and `/api/brain/model-design`.
- `server.js` also exposes `/api/brain/export-dataset`, and `/api/chat` can now request BRAIN context for a live Ken AI Chat turn.
- `pipe-r.html` now includes a BRAIN tab for compendium search, context pack building, model blueprint creation/saving, and dataset export.
- The chat panel now has a `Brain: ON/OFF` toggle plus a live BRAIN context status line so Ken AI Chat can operate as the main operator surface with indexed retrieval.
- Saved designs now land in `brain/designs/`.
- Saved training artifacts now land in:
  - `brain/exports/`
  - `brain/training_specs/`
