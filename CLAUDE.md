# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Pipe-R v4.0 — a Node.js project orchestration command center. Button-driven terminal UI + HTTP API + agent dispatch system + Google Sheets backup layer. No external dependencies — uses only Node.js built-in modules.

## Running

```bash
node hub.js        # Terminal UI (interactive, blocking)
node server.js     # HTTP API on :7777 (background, includes auto-sync)
```

No `npm install` needed. Both scripts are standalone.

Desktop shortcut scripts (double-click from `C:\Users\Ken\Desktop\Pipe-R Scripts\`): `START SESSION.bat`, `STOP SERVER.bat`, `OPEN HUB.bat`, `STATUS.bat`, `OPEN LOGS.bat`, `SESSION NOTES.bat`. See the folder's README.txt for the daily flow.

**Stopping a background server:** `tasklist //FI "IMAGENAME eq node.exe"` to find the PID, then `taskkill //PID <pid> //F`. The `STOP SERVER.bat` script does this interactively.

## Architecture

- **hub.js** (~3,440 LOC) — Terminal TUI. All interaction through numbered buttons and letter keys. `mainMenu()` is the entry point. Each menu is a function (e.g., `projectsMenu()`, `taskBoard()`, `sheetsMenu()`). New features need a menu function wired into `mainMenu()`. Press `M` for Agent Mode, `G` for Google Sheets.
- **server.js** (~580 LOC) — HTTP server on port 7777. REST endpoints under `/api/*`. Serves web UIs (`pipe-r.html`, `remote.html` — not yet built). New endpoints go before the 404 handler. Has a 30-second auto-executor loop for queued agent tasks and a 15-minute auto-sync for Google Sheets.
- **agent_mode/** — Hybrid AI framework + Google Sheets sync layer.
  - `core/orchestrator.js` — Task dispatch, auto-assign, batch execution, review flow
  - `core/queue.js` — Persistent task storage (JSON) with status tracking
  - `core/registry.js` — Agent profiles, roles, personalities, completion metrics
  - `core/executor.js` — Builds prompts with file context, runs against Ollama, captures training data
  - `config/` — `runtime.json` (mode settings), `agents.json` (registered models), `tasks.json` (task queue)
  - `training/training-log.jsonl` — Every prompt/response pair saved for model improvement
  - `sheets/auth.js` — Google OAuth2 token management, one-time browser auth on port 9999
  - `sheets/schema.js` — 8 tab definitions (Roster, Timecards, Tasks, MROs, Incidents, Certifications, JSAs, Crew Info) with headers, formatting, validation, protection rules
  - `sheets/sync.js` — Push (Supabase → Sheets) and Pull (Sheets → Supabase) sync engine. Config tracks per-crew spreadsheet IDs and sync timestamps

## Agent Mode

Seven Ollama models registered with specialized roles:
- **Qwen Coder** (14B) — Patch Drafter, primary code brain
- **ForgeAgent** — General Worker
- **CHERP Piper** — Construction domain knowledge (not code — fine-tuned for field specs)
- **Llama 3.1** (8B) — Log Summarizer
- **Jeffery** — Test Builder (conservative)
- **Jefferferson** — Memory Curator
- **Ken AI** — Personality Lead, built from `agent_mode/ken/profile.md` on top of qwen2.5-coder. Status: `pending_build` — run `ollama create ken-ai -f agent_mode/ken/Modelfile` to activate.

Route code tasks to Qwen/ForgeAgent. Route construction domain queries to CHERP Piper. Route Ken-style work to Ken AI once built.

### Known Issues / Gotchas

- **`jefferferson:latest`** consistently times out on `ollama run` (spawnSync ETIMEDOUT). Don't route tasks to it until fixed or replaced.
- **Executor has no max-retry cap.** Failed tasks stay `queued` and the 30s auto-exec loop retries them forever with no backoff. Mark stuck tasks `status: "failed"` manually in `agent_mode/config/tasks.json` until a retry cap lands in `orchestrator.js`.
- **`tasks.json` is held in memory by the running server.** Editing the file while `server.js` is live gets clobbered on next save. Stop the server first, edit, then restart.

## Google Sheets Sync

Dual-purpose system: backup + customer-facing feature for clients who prefer spreadsheets. One Google Spreadsheet per crew with 8 tabs mirroring Supabase tables.

- **Push sync** (Supabase → Sheets): Replaces all data rows, preserves headers. Runs on manual trigger or auto-sync timer.
- **Pull sync** (Sheets → Supabase): Editable tabs only (Roster, Timecards, Tasks, MROs). Diffs against DB, won't create new rows — safety measure.
- **Auto-sync**: server.js pushes every 15 minutes when auth token exists and crews are configured.
- **Hub.js**: Press `G` → Sync Now, Pull Changes, Create Crew Sheet, Status, Open in Browser, Authorize.
- **Server.js endpoints**: `POST /api/sheets/sync`, `POST /api/sheets/pull`, `GET /api/sheets/status`, `POST /api/sheets/create`.
- **Auth**: OAuth2 via Google Cloud project `cherp-493003`. First run opens browser on :9999 for consent. Tokens auto-refresh.
- **Security**: `token.json`, `config.json`, `credentials.json` are all gitignored. Supabase service key passed at runtime via env var.

When adding new CHERP tables to sync: add tab definition in `schema.js` TABS array, then add query logic in `sync.js` pushSync/pullSync.

## Ken AI (Personality Layer)

`agent_mode/ken/` holds the personality layer for Ken's AI coding assistant.

- **`profile.md`** — canonical voice, coding rules, hard no's, and domain knowledge. Source of truth. Edit this to tune the personality; everything downstream reads from here.
- **`Modelfile`** — Ollama recipe: `FROM qwen2.5-coder:14b` + profile as `SYSTEM` prompt. Rebuild with `ollama create ken-ai -f agent_mode/ken/Modelfile` after editing `profile.md`.
- **`README.md`** — setup instructions and verification steps.

The **`ken-coder` personality** is wired into `executor.js`: any existing agent can run in Ken's voice today by setting `personality: "ken-coder"` in `agents.json`. The executor loads `profile.md` fresh at startup — no rebuild needed for personality-only changes.

Training data from every Ken AI task flows into `agent_mode/training/training-log.jsonl`, building the dataset for a future real fine-tune. Curation script (`curate.js`) is deferred until there's enough data to justify it.

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

## CHERP (Related — HesKenY/CHERP, private repo)

Construction crew management platform deployed to cherp.live via Netlify. Key things to know when working on CHERP from this repo:
- **Local clone:** `workspace/CHERP` (gitignored) — pull with `gh repo clone HesKenY/CHERP` inside `workspace/` if missing
- **Supabase project:** `nptmzihtujgkmqougkzd` — master schema in `cherp-schema.sql`
- **netlify.toml CSP:** `connect-src` must include the Supabase project URL or API calls silently fail
- **Branch strategy:** `main` auto-deploys to cherp.live, `dev` branch for testing
- **Service worker:** Can cache stale files. Bump cache version or use one-time buster when deploying breaking changes
- **Hardcoded fallback users** in `js/config.js` allow PIN login when Supabase is unreachable

## Related Repos

| Project | Repo | Domain | Notes |
|---------|------|--------|-------|
| CHERP | HesKenY/CHERP (private) | cherp.live | Construction crew management platform |
| Bird's Nest | HesKenY/CHERP-Nest | — | Backend superuser/instance manager |
| Pipe-R | HesKenY/Pipe-R | — | This repo |
| CodeForge | HesKenY/CodeForge | codesforge.netlify.app | — |

## Future / In-Progress

- **Google Cloud for Nest wizard**: When the Bird's Nest Instance Builder publishes custom CHERP instances, it needs Google Cloud integration steps — creating per-instance Google Sheets, setting up Drive storage, and provisioning OAuth credentials as part of the wizard flow. This is not built yet.
- **Ken AI v2 (real fine-tune)**: v1 scaffold shipped 2026-04-11 (`agent_mode/ken/`). Next step is the curation script + actual fine-tune once training-log.jsonl has enough clean entries.
- **CHERP web integration**: Add `sheet_url` column to `team_codes` in Supabase. CHERP web app shows "View in Sheets" button so customers can access their crew's spreadsheet directly from cherp.live.
- **Web UIs**: `pipe-r.html` and `remote.html` referenced by server.js but not yet built.
- **Nest dependency install hook**: Bird's Nest wizard should check for Node.js (and future deps) during instance generation, prompt for permission, and install if missing. Extensible pattern — no silent installs.
- **CHERP home screen auto-refresh**: Live-update `mycrew.js` when Supabase/Sheets data changes so users don't need to manually reload.
- **Executor retry cap**: Add a max-retries field to `orchestrator.js` so failed tasks stop looping after N attempts with exponential backoff.
