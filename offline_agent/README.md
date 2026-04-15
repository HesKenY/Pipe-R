# offline_agent — Ken AI (offline Claude)

A fully offline coding agent that runs on Ken's machine via
Ollama. No cloud. No telemetry. No hosted wrapper. Built as a
**local equivalent to Claude Code** — same discipline (read
before write, propose before execute, kill switch, layered
permissions, full audit trail) — but with everything on the
box and the brain in Ken's voice.

**Port:** `http://localhost:7778` (Pipe-R owns 7777)
**Version:** 0.1.0-skeleton

## Design intent

Ken already uses Claude Code for coding work. This project
is the offline mirror: when he doesn't want to depend on the
cloud, or when a task has to run overnight across sensitive
local files, or when he's training a proprietary model for
his own machine — `offline_agent` is the one he runs.

Key differences from a hosted agent:

- every model inference goes through local Ollama, never a
  remote API
- the planner reads Ken's **BRAIN** (`brain/brain_index/` +
  `brain/sessions/` + `brain/tasks/`) for context, not a
  stateless chat history
- every response is filtered through Ken's voice profile
  (ken-ai:latest is the planner model, not a generic coder)
- every write is logged, backed up, and rollbackable
- mode escalation requires operator confirmation (Ken
  himself or the kill switch file)

## Quick Start

```bat
:: 1. install Ollama (https://ollama.com) and pull at least:
ollama pull ken-ai:latest
ollama pull qwen2.5-coder:14b
ollama pull llama3.2-vision

:: 2. install python deps (FastAPI + uvicorn + PyYAML + pyautogui + httpx)
pip install -r requirements.txt

:: 3. run
python main.py

:: 4. open http://localhost:7778 in a browser
```

## Permission Modes (Claude Code pattern)

Start in **Mode 0**. Only escalate when the task needs it.

| Mode | Name | Capability |
|------|------|------------|
| 0 | Read Only | Read files, search, plan, read brain. No writes. |
| 1 | Workspace | Edit files in workspace/ + brain/, run tests + formatters + linters, git add/commit. |
| 2 | Elevated Dev | Install packages, Docker, take screenshots. |
| 3 | Operator | Full desktop automation (mouse/keyboard/hotkeys). Kill switch must be armable. |

Every tool call goes through `tool_router.py` which checks
`permissions.check(tool, path)` — including blocked paths
(system dirs, `.ssh`, `.env`) regardless of mode. The kill
switch file (`config/.kill_switch`) always wins.

## Architecture

```
offline_agent/
├─ main.py                       FastAPI + WebSocket on :7778
├─ agent_core/
│  ├─ planner.py                 main loop (read → plan → tool → log)
│  ├─ permissions.py             mode enforcement + kill switch
│  ├─ memory_retriever.py        SQLite FTS5 over brain
│  ├─ session_manager.py         per-turn log → brain/sessions/
│  ├─ tool_router.py             tool dispatch + permission check
│  ├─ patch_engine.py            read → diff → backup → apply
│  ├─ vision.py                  llama3.2-vision screenshot read
│  └─ desktop_controller.py      pyautogui (Mode 3 only)
├─ models/
│  └─ ollama_client.py           HTTP API wrapper + ANSI strip
├─ tools/
│  ├─ filesystem_tools.py        read/list/write/patch
│  ├─ git_tools.py               status/diff/log/add/commit/stash
│  ├─ shell_tools.py             run_command/tests/formatter/lint
│  ├─ search_tools.py            ripgrep/find/grep/count
│  ├─ ui_tools.py                screenshot + Mode 3 input
│  ├─ memory_tools.py            brain read/write/task/session
│  └─ drill_tools.py             halo-trainer classroom bridge
├─ config/
│  ├─ permissions.yaml           the 4 mode rules
│  ├─ models.yaml                Ollama profiles (planner/coder/vision/...)
│  ├─ tools.yaml                 tool definitions
│  └─ projects.yaml              Ken's real 5 projects
├─ brain/
│  ├─ brain_index/               source-of-truth markdown
│  │  ├─ identity.md             who the agent is + voice rules
│  │  ├─ rules.md                CHERP gotchas, git rules, voice
│  │  ├─ tech_stack.md           stack + port map + Ollama roster
│  │  ├─ project_map.md          every Ken project in 4 tiers
│  │  ├─ repo_map.md             git remotes + clones + branches
│  │  ├─ known_fixes.md          14 patterns + fixes
│  │  ├─ claude_project_brief.md (imported from ../CLAUDE.md)
│  │  ├─ agents_coordination.md  (imported from ../AGENTS.md)
│  │  ├─ ken_voice_profile.md    (imported from pipe-r notes)
│  │  └─ cherp_schema.sql        (imported from CHERP repo)
│  ├─ sessions/YYYY-MM-DD/
│  │  └─ session_log.md          today's running log
│  ├─ tasks/
│  │  ├─ open/*.md               active work
│  │  └─ done/*.md               completed
│  ├─ model_designs/<slug>/
│  │  └─ design.json             proprietary model design (9-field schema)
│  ├─ training/
│  │  ├─ specs/                  Codex-compat training specs
│  │  ├─ datasets/               built JSONL datasets
│  │  └─ training-log-recent.jsonl (imported from pipe-r)
│  ├─ corpus/
│  │  └─ halo-trainer-*.jsonl    imported curated rows
│  ├─ brain_build.py             read import_manifest.yaml → pull external context
│  ├─ model_designer.py          validate + build dataset + emit spec
│  └─ SCHEMA.md (under model_designs/) the design contract
├─ frontend/
│  └─ index.html                 the UI
├─ logs/
│  ├─ memory.db                  FTS5 index (rebuilt on boot)
│  ├─ actions.jsonl              every tool call, audited
│  ├─ backups/                   pre-write file backups
│  └─ screenshots/               Mode 2+ capture output
└─ workspace/                    sandbox for throwaway edits
```

## Safety

- **Kill switch**: `config/.kill_switch` file OR UI button halts
  the agent instantly. Every tool call checks it first.
- **Backups**: `patch_engine.py` writes the pre-edit content to
  `logs/backups/` before applying any file write. Rollback is
  always available.
- **Audit log**: every tool call appends to `logs/actions.jsonl`
  with `{ts, tool, params, result_preview, permitted, step, task}`.
- **Dry run default**: `permissions.yaml` has `dry_run_default: true`
  so writes are simulated unless explicitly confirmed.
- **Path guards**: `blocked_paths` list (C:/Windows, ~/.ssh,
  ~/.aws, credentials files) enforced regardless of mode.

## Brain layout (Ken's spec, 2026-04-14)

The brain is the agent's long-term memory. Every major piece
of context lives as markdown so Ken can read it, edit it, and
version-control it. The FTS5 SQLite DB is rebuilt from the
markdown on every boot — it's a cache, not the source of truth.

Baseline files that are ALWAYS injected into the planner
prompt: `identity.md` + `rules.md`. Everything else comes in
via top-K FTS retrieval.

Refresh the brain from external sources (Claude's CLAUDE.md,
Pipe-R's training-log.jsonl, halo-trainer's corpus/, CHERP
schema) by running:

```bat
python brain/brain_build.py --once
```

## Model Designer

`brain/model_designer.py` is the pipeline for planning and
training a proprietary offline developer model.

Follows the 9-field schema from `Codex/brain/MODEL_DESIGNER_SPEC.md`:
mission, capabilities, permissions, memory strategy, dream
strategy, training sources, evaluation goals, runtime plan,
rollout risks.

```bat
python brain/model_designer.py list
python brain/model_designer.py validate ken-ai-offline-v0
python brain/model_designer.py full ken-ai-offline-v0
```

The `full` subcommand validates → builds a JSONL dataset from
the design's training_sources → emits a training spec matching
the Codex schema so both workbenches speak the same language.

## Ollama roster (Ken's machine)

| Profile | Model | Use |
|---------|-------|-----|
| planner | `ken-ai:latest` | main loop, Ken's voice |
| coder | `qwen2.5-coder:14b` | code gen + patching |
| reviewer | `qwen2.5-coder:14b` (temp 0) | diff review |
| vision | `llama3.2-vision` | screenshot + HUD reading |
| fast | `llama3.1:8b` | quick summaries, JSON patches |
| recon | `cherp-piper:latest` | codebase mapping |
| integration | `forgeagent:latest` | module wiring |
| quality | `jefferyjefferferson:latest` | QA + rubric scoring |
| tutor | `m3w-learning:latest` | prompt tuning |

Swap profiles in `config/models.yaml`. Fallback chain is:
ken-ai → qwen → llama3.1 → qwen7b.

## Adding your project

Edit `config/projects.yaml`. The default config already knows
about Ken's 5 real projects: Pipe-R, Claude clone, halo-trainer,
CHERP, and this project itself.

## Related

- **Pipe-R** — Node.js command center at 127.0.0.1:7777
  (`../server.js`, `../hub.js`). Same clone.
- **halo-trainer** — classroom scoring drills for the agent
  squad. `../halo-trainer/`. offline_agent's `drill_tools`
  bridges to it via node subprocess.
- **Model Designer** — the tool backed by BRAIN, spec at
  `../brain/MODEL_DESIGNER_SPEC.md` (Codex side).
