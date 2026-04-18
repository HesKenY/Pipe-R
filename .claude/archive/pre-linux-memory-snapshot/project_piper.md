---
name: Pipe-R — Project Command Center
description: Pipe-R is a Node.js project orchestrator with terminal TUI (hub.js), HTTP server (server.js on :7777), and planned sci-fi web UI.
type: project
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
Pipe-R v4.0 is Ken's personal command center for managing all his projects. It has three layers:

1. **hub.js** (~3K LOC) — Terminal TUI with button-driven menus, project management, agent dispatch, task board, git ops
2. **server.js** — HTTP API on port 7777, serves web UI and remote client, unified backend
3. **Web UI** (planned) — Sci-fi "command deck" browser interface (spec in CLAUDE_BUILD_INSTRUCTIONS.md)

**Folder convention:**
- `input/` — Source projects dropped in for work
- `output/` — Finished deliverables and packaged builds
- `workspace/` — Active in-progress work
- `staging/` — Review-ready artifacts
- `.claude/logs/` — Runtime logs (hub.log, server.log)

**Why:** Ken manages multiple projects (CHERP, Bird's Nest, CodeForge, REVV) from this single hub. The orchestrator pattern lets him control everything without writing code.

**How to apply:** Changes to hub.js or server.js must preserve the button-driven UX. The folder pipeline (input -> workspace -> staging -> output) is a core workflow — respect it.
