# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Pipe-R v4.0 — a Node.js project orchestration command center. Button-driven terminal UI + HTTP API + agent dispatch system. No external dependencies — uses only Node.js built-in modules.

## Running

```bash
node hub.js        # Terminal UI (interactive, blocking)
node server.js     # HTTP API on :7777 (background)
```

No `npm install` needed. Both scripts are standalone.

## Architecture

- **hub.js** (~3,240 LOC) — Terminal TUI. All interaction through numbered buttons and letter keys. `mainMenu()` is the entry point. Each menu is a function (e.g., `projectsMenu()`, `taskBoard()`, `gitMenu()`). New features need a menu function wired into `mainMenu()`.
- **server.js** (~522 LOC) — HTTP server on port 7777. REST endpoints under `/api/*`. Serves web UIs (`pipe-r.html`, `remote.html` — not yet built). New endpoints go before the 404 handler. Has a 30-second auto-executor loop for queued agent tasks.
- **agent_mode/** — Task orchestration framework. `Orchestrator` class handles task creation, execution, review, and agent assignment. Supports hybrid/offline modes. Agent profiles go in `agent_mode/agents/profiles/`.

## Folder Pipeline

```
input/     → Drop source files here
workspace/ → Active work in progress
staging/   → Ready for review
output/    → Finished deliverables and zips
```

All four directories are gitignored and auto-created by hub.js on boot. `Desktop/` is also gitignored — contains separate projects.

## Projects Registry

Projects are hardcoded in both `hub.js` (lines ~236) and `server.js` (lines ~26). Keep them in sync when adding/removing projects. Each project has a name, path, codename, and optional URL/repo.

## Logging

- Runtime logs: `.claude/logs/hub.log` and `.claude/logs/server.log`
- In hub.js use `hubLog(level, message)`
- In server.js use `log(message)`
- Session checkpoints: `.claude/SESSION_LOG.md`

## Key Rules

- **Button-driven UX only.** The user is a non-coder. No free-text commands in the TUI except when explicitly prompted (file names, notes). Every feature needs a button.
- **Sci-fi dark theme.** ANSI 256-color palette with blues, cyans, greens, ambers. Box-drawing characters for UI chrome. Don't introduce flat/material design.
- **Windows environment.** Uses `powershell` for ZIP, `explorer` for file browsing, Windows paths. Shell commands must work in Git Bash on Windows.
- **No external deps.** Hub and server use only Node.js built-ins (fs, path, http, readline, child_process). Keep it that way.
- **Web UIs don't exist yet.** `pipe-r.html` and `remote.html` are referenced by server.js but not built. Spec is in `CLAUDE_BUILD_INSTRUCTIONS.md`.

## Related Repos

| Project | Repo | Domain | Notes |
|---------|------|--------|-------|
| CHERP | HesKenY/CHERP | cherp.live | Construction crew management platform |
| Bird's Nest | HesKenY/CHERP-Nest | — | Backend superuser/instance manager |
| Pipe-R | HesKenY/Pipe-R | — | This repo |
| CodeForge | HesKenY/CodeForge | codesforge.netlify.app | — |
