# offline_agent - KenAI Offline Developer

A fully local coding agent that runs on Ken's machine through Ollama.
No cloud. No telemetry. No hosted wrapper.

This is the coding-first local workbench for the `ken v4 offline
developer` goal: a repo-aware assistant that reads the brain, works
inside the Codex clone, respects the Claude peer-clone boundary, and
helps with the mechanical software work that normally lives in a tool
like Claude Code.

Port: `http://localhost:7778`
Version: `0.4.1`

## What changed

- default runtime now targets `kenai:v4-offline-developer`
- automatic planner fallback keeps the app usable if that tag is not
  built locally yet
- the workbench now exposes squad-lead state from `agent_mode` so V4
  can see the live roster, queue, and lead-sync gap
- the live `agent_mode` trainer pin is now promoted to
  `kenai:v4-offline-developer` with compatibility fallback to
  `ken-ai:latest`
- Halo and game-focused runtime surfaces were removed from the server
  and UI
- permissions now map to the real registered coding tools
- write roots are aligned to the actual Codex clone instead of a tiny
  internal sandbox
- brain imports and model design now center on coding work, not game
  loops

## Core idea

Ken already uses cloud coding agents. `offline_agent` is the local
version:

- reads the BRAIN before acting
- works through a mode-based permissions system
- patches carefully and logs everything
- understands Codex vs Claude working-tree boundaries
- can run tests, formatters, git, and local shell commands
- keeps durable task/session memory
- acts as the coding-first lead view for the local agent squad

## Quick start

```bat
cd offline_agent
setup.bat
START.bat
```

Or run the v4 seed model directly:

```bat
KENAI_v4.bat
```

## Permission modes

| Mode | Name | Purpose |
|------|------|---------|
| 0 | Read Only | Scan repos, read brain, plan work. |
| 1 | Workspace Write | Patch code in the Codex clone, update brain notes, run safe dev commands. |
| 2 | Elevated Dev | Package installs, screenshots, richer local inspection. |
| 3 | Operator Mode | Desktop input automation and hotkeys. Confirm first. |

## Main surfaces

- `main.py` - FastAPI + WebSocket server on `:7778`
- `frontend/index.html` - coding workbench UI
- `agent_core/planner.py` - planner loop and tool orchestration
- `agent_core/squad_state.py` - read-only squad snapshot bridge into `agent_mode`
- `agent_core/permissions.py` - mode enforcement, path guards, kill switch
- `models/ollama_client.py` - Ollama wrapper with automatic local fallback
- `brain/` - long-term memory, tasks, design specs, imports

## Squad lead surface

Ken V4 offline developer is the intended lead for the local coding
squad. The workbench now reads:

- `agent_mode/config/agents.json`
- `agent_mode/config/runtime.json`
- `agent_mode/config/tasks.json`

That gives the offline runtime a clean view of:

- the intended V4 lead model
- the current live runtime trainer pin
- roster health and blocked agents
- queued squad work that still needs attention

The shared runtime is now pinned to the V4 trainer id as well, but the
agent squad still falls back to `ken-ai:latest` if the newer tag has not
been built locally yet.

## Model direction

Target model: `kenai:v4-offline-developer`

The app now prefers that tag, but if it is not present locally it will
fall back automatically in this order:

1. `kenai:v3`
2. `ken-ai:latest`
3. `qwen2.5-coder:14b`
4. `llama3.1:8b`

That gives you a stable coding runtime today while keeping the default
pointed at the intended V4 direction.

## Brain refresh

The brain importer now focuses on:

- `CLAUDE.md`
- `AGENTS.md`
- `.claude/CODEX_BRIEF.md`
- `.claude/WORKLIST.md`
- `agent_mode/AGENT_SAFETY_RULES.md`
- recent training log history
- selected repo references like the CHERP schema

Refresh manually:

```bat
python brain/brain_build.py --once
```

## Building the seed v4 model

The repo now includes:

- `KENAI_v4.bat`
- `brain/training/modelfiles/kenai-v4-offline-developer.Modelfile`

That is a seed local developer tag, not the final fine-tuned endpoint.
It is enough to give the runtime a dedicated coding-first local model
name while the fuller V4 corpus and training pipeline keep evolving.
