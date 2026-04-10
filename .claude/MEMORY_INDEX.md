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
