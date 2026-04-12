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

Eight Ollama models registered with specialized roles (the party + trainer + companion):

| Slot | Badge | Display | Base model | Track |
|---|---|---|---|---|
| Trainer | TR | Ken AI | `ken-ai:latest` (from qwen2.5-coder:14b) | trainer / orchestrator |
| Party 1 | SCZ | 5c1z0r Patchsmith | `qwen2.5-coder:14b` | implementation |
| Party 2 | ROT | R0t0m Relay | `forgeagent:latest` | integration |
| Party 3 | DEC | D3c1du3y3 Pathfinder | `cherp-piper:latest` | recon |
| Party 4 | PGN | P0ryg0n Logdex | `llama3.1:8b` | observability |
| Party 5 | UMB | Umbr30n Safeguard | `jefferyjefferferson:latest` | quality |
| Party 6 | ALK | 4l4k4z4m Archive | `jefferferson:latest` | memory (slow cold start — see Known Issues) |
| Companion | M3W | M3w Promptdex | `m3w-learning:latest` (from llama3.1:8b) | learning |

Route code tasks to Qwen/ForgeAgent. Route construction domain queries to CHERP Piper. Route Ken-style work to Ken AI. Route prompt-tuning / post-task learning to M3w.

M3w was built 2026-04-12 from `agent_mode/m3w/Modelfile` (FROM llama3.1:8b + SYSTEM profile from `agent_mode/m3w/profile.md`). Rebuild after profile edits: `ollama create m3w-learning -f agent_mode/m3w/Modelfile`.

### Per-agent memory system (2026-04-12)

Every registered agent gets its own directory under `agent_mode/memories/<slug>/` (slug = id with colons replaced by hyphens). `server.js` scaffolds these at boot via `agent_mode/core/memory.js` ensureAllMemoryDirs. Each dir contains:

- **`notes.md`** — durable, editable standing instructions + facts. Injected into every chat turn AND every dispatched task by `executor._buildPrompt()`. Source of truth for "I always want agent X to do Y". Edit the file or use the deck's Notes button.
- **`chat-log.jsonl`** — append-only audit of every chat turn (role, content, ts). Cleared by the deck's Clear button (hits `DELETE /api/chat/:agentId/log`).
- **`charter.md`** — mirror of the agent's training charter, copied from `agent_mode/training/charters/` on first boot.

The same `notes.md` loader runs in both the chat endpoint (`POST /api/chat`) and the executor's task dispatch path (`executor.js _buildPrompt`), so there is ONE source of truth per agent. Write it once, it applies everywhere.

### Deck + chat surface (2026-04-12)

- **`DECK.bat`** — single-click launcher. Starts server, waits for :7777, co-launches Nest if present, opens Chrome `--app` mode at 1920×720 pointing at `pipe-r.html?deck=1`. Pure chromeless window.
- **`pipe-r.html?deck=1`** — control deck layout mode. Left stack: Trainer (with Ken AI pixel portrait from `trainer-ken.jpg`), Party row (6 cards horizontal), Queue (Board tab only). Right stack: Stats screen (dominant, ~55% of column) + Chat panel + 3 mini info panels. Two-tab system (`Deck` / `Board`) switches which panels are visible. Agent Mode ON/OFF toggle button (maps to pause-agents/resume-agents).
- **Chat panel**: tied to selected agent. Persistent history via `/api/chat` endpoints. Loads charter + notes + last 12 turns into a fresh ollama run. Every turn also appends to `training-log.jsonl` with `taskType: "chat"` — chat builds the Ken AI v2 fine-tune corpus alongside dispatches.
- **Training log viewer**: Log button in chat panel opens an inline overlay showing the last 40 entries for the selected agent with Approve/Reject buttons (`POST /api/training/review`). Approved rows survive `curate.js --approved-only`.
- **Memory indicator**: yellow/green/cyan dot on each party + trainer card showing hasNotes / hasChatTurns state. Dashboard stamps `hasNotes`, `notesLength`, `chatTurns` on each agent.
- **Blocked agents**: agents with `"blocked": true` in `agents.json` are skipped by `orchestrator._tryAutoAssign` and render with a red `BLOCKED` badge on the deck + remote. Direct dispatch by id still works.
- **Remote deck**: `remote.html` is now a vertical stack mirroring the deck (Trainer Bench → Party → Stats → Chat → Dispatch → Queue). Fold 6 cover (≤420px) and inner (≥721px) breakpoints. PIN is **0615** (was 1996 — updated in `runtime.json` and the server.js fallback).

### API surface (post-2026-04-12)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/dashboard` | GET | full state; agents enriched with `hasNotes`, `notesLength`, `chatTurns`, `blocked`, `blockReason` |
| `/api/chat` | POST | `{ agentId, message }` → runs ollama, appends both turns to chat-log.jsonl + training-log.jsonl, returns `{ reply }` |
| `/api/chat/:agentId` | GET | recent chat history + notes.md contents |
| `/api/chat/:agentId/notes` | PUT | overwrite notes.md from the deck's notes editor |
| `/api/chat/:agentId/log` | DELETE | wipe chat-log.jsonl (training log stays intact) |
| `/api/chat/:agentId/training` | GET | last 40 training-log entries for this agent |
| `/api/training/review` | POST | `{ lineNo, approved, notes? }` → marks training-log row reviewed |

### Known Issues / Gotchas

- **`jefferferson:latest`** (Alakazam Archive, slot 6) — cold start is slow (~90s to first token on a fresh load), but the model does respond. Unblocked 2026-04-12 after a successful direct smoke test. Do not route `summarize` / `memory_extract` tasks to it while it's cold — those task types have 30s executor timeouts and will throw. `draft_patch` / `draft_test` (120s) and `scan` / `learn` (60s) are safer entry points.
- **`tasks.json` is held in memory by the running server.** Editing the file while `server.js` is live gets clobbered on next save. Stop the server first, edit, then restart.
- **Executor retry cap** — merged from Codex rebuild 2026-04-12 (commit `a599eb9`). Max retries + exponential backoff live in `orchestrator.js`.
- **Ollama run spinner leak**: `ollama run` emits ANSI CSI / OSC terminal spinner codes into stdout. `server.js` strips them in the chat endpoint before writing to memory/log — if you add new ollama spawn paths, strip those sequences too (`\u001b\[\??[0-9;]*[a-zA-Z]` and `\u001b\][^\u0007]*\u0007`).
- **CHERP `crew_tasks.id` mismatch** — the table column is `BIGINT GENERATED ALWAYS AS IDENTITY`; Postgres rejects any client-provided id with `428C9`. `tasks.js saveTask()` was fixed 2026-04-12 to omit `id` from the POST payload and read the server-assigned row back via `Prefer: return=representation`. If you add any new POSTs against `crew_tasks`, do not send an id.

### Dispatch fix (2026-04-12)

The orchestrator had three combined bugs that made every agent produce garbage output:

1. `queue.js add()` hardcoded `assignedAgent: null`, silently dropping the agent parameter from `/api/dispatch`.
2. `orchestrator.js createTask()` didn't forward `opts.assignedAgent` to `queue.add()`, so `_tryAutoAssign()` always ran and overrode the caller's choice.
3. `executor.js` used `execSync` with the prompt passed as a quoted shell arg. Windows `cmd.exe` has an 8191-char limit and double-quote escaping corrupts multi-line SYSTEM prompts — Ken's 6 KB profile was arriving at the model as shell noise. Fixed by switching to `spawnSync('ollama', ['run', model], { input: prompt })` so the prompt goes through stdin.

After the fix (commit `02d0d6f` + server restart), dispatch respects `agent:` correctly and the training-log captures real in-voice ken-ai responses. Verified with three back-to-back dispatches that previously produced plumbing metaphors or factorial Python code.

## Git remotes

The Claude project folder (this repo) is a private git repo pushed to two remotes:
- **origin** → `https://github.com/HesKenY/CHERP-Backup.git` (primary, pushed by default; wiped + force-reset 2026-04-12 to serve as the Pipe-R backup destination)
- **pipe-r** → `https://github.com/HesKenY/Pipe-R.git` (secondary, legacy, still intact)

Both repos are private. CHERP-Nest (`https://github.com/HesKenY/CHERP-Nest.git`) and CHERP (`https://github.com/HesKenY/CHERP.git`) are separate repos with their own remotes.

## Related workstreams

- **`.claude/CODEX_REBUILD_INTEGRATION_PLAN.md`** — Codex is working on a Pipe-R rebuild in `C:\Users\Ken\Desktop\Pipe-R Rebuild (Codex)\workspace`. Plan file catalogs what they shipped (retry cap, web UIs, P0K3M0N trainer theming), flags high-risk merge conflicts (queue.js, executor.js, orchestrator.js, agents.json, profile.md), and proposes a merge procedure. Do not execute without Ken's go-ahead.

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

Training data from every Ken AI task flows into `agent_mode/training/training-log.jsonl`, building the dataset for a future real fine-tune. A `curate.js` script will filter out `success=false` rows, broken-agent outputs, and short responses. v1 is prompt-engineered (SYSTEM block in Modelfile); v2 will be a real fine-tune once the curated set reaches ~200 clean entries.

**Voice rule (2026-04-12):** Ken AI speaks AS Ken — lowercase, 3–10 word messages, typos left in, no pleasantries, no analogies, no "as an AI" disclaimers. Full rule in `~/.claude/projects/.../memory/feedback_ken_ai_voice.md`. Do NOT re-introduce the "use construction analogies" instruction when editing `profile.md` — that was the original voice bug.

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
