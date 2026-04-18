---
name: Logging & Session Convention
description: Runtime logs go in .claude/logs/, session checkpoints in .claude/SESSION_LOG.md, repo notes in .claude/MEMORY_INDEX.md.
type: reference
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
- **Runtime logs:** `.claude/logs/hub.log` and `.claude/logs/server.log` (git-ignored)
- **Session checkpoints:** `.claude/SESSION_LOG.md` — date, files changed, decisions, next steps
- **Repo navigation:** `.claude/MEMORY_INDEX.md` — folder/file map for quick orientation
- **Server port:** 7777 (HTTP API + web UI + remote client)
- **Netlify:** Used for deployed dashboards (remote.html, codesforge.netlify.app)
