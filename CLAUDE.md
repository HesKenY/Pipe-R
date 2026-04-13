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

### API surface (post-2026-04-12 / 13)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/dashboard` | GET | full state; agents enriched with `hasNotes`, `notesLength`, `chatTurns`, `blocked`, `blockReason` |
| `/api/chat` | POST | `{ agentId, message }` → runs ollama, appends both turns to chat-log.jsonl + training-log.jsonl, returns `{ reply }` |
| `/api/chat/:agentId` | GET | recent chat history + notes.md contents |
| `/api/chat/:agentId/notes` | PUT | overwrite notes.md from the deck's notes editor |
| `/api/chat/:agentId/log` | DELETE | wipe chat-log.jsonl (training log stays intact) |
| `/api/chat/:agentId/training` | GET | last 40 training-log entries for this agent |
| `/api/training/review` | POST | `{ lineNo, approved, notes? }` → marks training-log row reviewed |
| `/api/livetest/scenarios` | GET | list available Live Test scenarios |
| `/api/livetest/rounds` | GET | list last 40 rounds (summary view) |
| `/api/livetest/rounds/:id` | GET | full round record with ops + team outputs |
| `/api/livetest/start` | POST | `{ scenarioId, teamCode?, mode?: 'v0'\|'v1', cleanup? }` — fires a round |
| `/api/livetest/results` | GET | last 100 round summaries from `results.jsonl` |
| `/api/livetest/patch-plan` | POST | `{ roundId? }` — asks Claude to draft a structured markdown patch plan for a round |
| `/api/livetest/patches` | GET | list saved patch plans |
| `/api/livetest/patches/:id` | GET | single patch plan as JSON |
| `/api/queue/run` | POST | execute queued tasks through orchestrator (up to 10 per call) |
| `/api/review/auto-run` | POST | `{ max? }` — call `claude -p` on each `waiting_for_claude` task, APPROVE/REJECT via orch.reviewTask |
| `/api/auto/generate-tasks` | POST | `{ count? }` — ask Claude for N new dispatchable tasks as JSON, createTask each |
| `/api/metrics` | GET | CPU / RAM / GPU / disk / loaded ollama models (2s cache) |
| `/api/now-playing` | GET | Windows SMTC currently-playing media (1.5s cache) |
| `/api/now-playing/control` | POST | `{ action: play\|pause\|toggle\|next\|prev }` — fires SMTC transport |
| `/api/volume` | GET/POST | read/set system + per-app (Spotify) volume via Core Audio COM |
| `/api/wallpaper-colors` | GET | dominant colors from current main-display wallpaper (for auto theme) |
| `/api/macro/send` | POST | `{ key: enter\|space\|tab\|f15\|esc }` — SendKeys macro into foreground window |
| `/api/shell/run` | POST | `{ command }` — runs a PowerShell command (auto-wraps bare `claude <text>` into `claude -p "..."`) |
| `/api/steam/library` | GET | installed Steam games from libraryfolders.vdf + localconfig.vdf playtime |
| `/api/dl/:filename` | GET | serve a file from the input/ folder (for Tailscale/LAN file transfer) |

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

- **`.claude/CODEX_REBUILD_INTEGRATION_PLAN.md`** — Codex is working on a Pipe-R rebuild in `C:\Users\Ken\Desktop\Pipe-R Rebuild (Codex)\workspace`. Plan file catalogs what they shipped (retry cap, web UIs, trainer theming), flags high-risk merge conflicts (queue.js, executor.js, orchestrator.js, agents.json, profile.md), and proposes a merge procedure. Do not execute without Ken's go-ahead.
- **`.claude/WORKLIST.md`** — running punch list + Live Test Mode design brief. Edit freely; Claude reads it at the start of a session.

## Live Test Mode (2026-04-12)

`agent_mode/core/livetest.js` runs a scripted scenario against a real CHERP instance and asks an observer agent for a debrief. Default target: `https://cherp.live/demo.html` + team_code `WS5A3Q` (standing Test crew on production — pass `teamCode: "WS5A3Q"` to `POST /api/livetest/start` to reuse it instead of creating a new SIMLT-<random> crew).

**Phases per round:**
1. `signup_user` — creates `user_profiles` for each sim member (SHA-256 PIN, role-valid)
2. `create_crew` — skipped when `reuseExistingCrew` is set, otherwise inserts `team_codes`
3. `user_join_crew` + `add_member` — PATCH each user's `team_code`, then insert `crew_members`
4. `create_task` — `crew_tasks` POST with `Prefer: return=representation` so the bigint id comes back
5. `progress_update` — PATCH progress + notes on the tasks just created
6. `timecard` — `crew_timecards` with client-gen TEXT id, correct `user_id`/`user_name`/`hours`/`date`
7. `daily_log` — `daily_logs` (no team_code column; uses `company_id` + `created_by` UUID)
8. `crew_message` — `messages` (sender_id UUID + `channel` field for the team code)
9. `cleanup` — reverse order by row id, tolerant to FK residue (foreman user_profile often returns 409 due to audit_log FK — benign)

**Scenarios:** `agent_mode/livetest/scenarios/*.json`. Current catalog:
- `kitchen-remodel-3day` — 3-person crew, 5 tasks, 3 progress updates, one day. Verified 37/38 green against live cherp.live.

**Rounds** persist to `agent_mode/livetest/rounds/<roundId>.json` with the full operation log + observer debrief. `curate.js` picks up the debrief turns as `taskType: "chat"` rows in `training-log.jsonl` automatically.

**Endpoints:**
- `GET /api/livetest/scenarios` — list available scenarios
- `GET /api/livetest/rounds` — list last 40 rounds
- `GET /api/livetest/rounds/<id>` — full round with operations + debrief
- `POST /api/livetest/start` — fire a round with `{ scenarioId, teamCode?, instanceUrl?, observer?, cleanup? }`

**v1 ambitions (queued in WORKLIST.md):** split the 6 agents into Team A (Crew Roleplay: D3c1du3y3/5c1z0r/P0ryg0n) and Team B (Ops+Maint: R0t0m/Umbr30n/4l4k4z4m); parallel dispatch; multi-scenario dropdown in the deck; pass/fail scoring against `acceptCriteria`.

## System telemetry + now playing (2026-04-12)

- **`GET /api/metrics`** — cached 2s, pulls CPU/RAM/disk via PowerShell + GPU via `nvidia-smi` + loaded models via `ollama ps`. CPU temp is usually null on AMD (WMI thermal zone empty).
- **`GET /api/now-playing`** — cached 1.5s, reads Windows SMTC via `.claude/bin/smtc-nowplaying.ps1`. No OAuth — just the currently playing track from Spotify desktop or any SMTC-aware app. Keeps the deck's now-playing strip live with whatever's running on Ken's system.

## Deck (2026-04-12 vaporwave pass)

- **`DECK.bat`** — chromeless Chrome `--app` launcher at 1920×720 pointing at `pipe-r.html?deck=1`.
- **Theme:** vaporwave-ops (purple/cyan), Orbitron + Inter fonts, chrome-gradient h1, 5 theme presets in Settings (Vaporwave / Outrun / Terminal / Arctic / Blood) via body[data-theme] CSS vars.
- **Tabs:** Deck / Board / Metrics. Deck tab hides info panels; Board tab shows queue+projects+sheets+activity; Metrics tab shows 8 circular SVG gauges + loaded Ollama models.
- **Settings modal:** ⚙ button in the audio strip. Theme picker, refresh interval, audio source, PIN display, Agent Mode toggle.
- **Notes modal:** per-agent `notes.md` editor as a full-screen overlay (not inline — it used to squash the chat).
- **Chat panel:** tied to selected agent, live loop against `/api/chat`, turns feed both `chat-log.jsonl` and `training-log.jsonl`. Log button opens a training-log viewer overlay with Approve/Reject buttons per row.
- **Now Playing strip:** shows SMTC data, pulsing dot on playback, source badge.

## Session 2026-04-12 / 13 — what shipped

Big-ticket additions this session. Everything below is live, committed, and
verified — read this to catch up on what exists before proposing new work.

### Live Test Mode (v0 + v1)

`agent_mode/core/livetest.js` runs scripted scenarios against a real CHERP
instance + optionally fans out to the full agent squad. Two modes:

- **v0** (`runRound`): one observer agent (P0ryg0n) reads the operation log
  and writes a debrief. Scripted CHERP operations: signup user_profiles,
  create crew (or reuse), add crew_members, create crew_tasks, progress
  updates, timecards, daily log, crew message, reverse-order cleanup.
- **v1** (`runRoundV1`): layers the 6-agent dual-team split on top of v0's
  operation engine. Team A (D3c1du3y3 Foreman / 5c1z0r Worker / P0ryg0n
  Apprentice) roleplays the crew. Team B (R0t0m Integration / Umbr30n QA /
  4l4k4z4m Archive) audits from the outside. Ken AI makes the trainer
  decision. M3w proposes one prompt/notes improvement. Each round persists
  to `agent_mode/livetest/rounds/ltv1-<id>.json`.

**Default target**: `cherp.live/demo.html` + `team_code=WS5A3Q` (standing
Test crew). Pass `reuseExistingCrew` or `teamCode` to the runner to point
at a pre-existing crew — cleanup will only remove rows the round itself
created, keyed by the `simlt-<team>-<name>` device_id pattern. **Never
lets cleanup drop `team_codes?code=eq.<teamCode>` when reuse is set** —
this was the critical bug caught by the first patch plan.

Scenarios: `agent_mode/livetest/scenarios/kitchen-remodel-3day.json` —
1 foreman + 3 journeymen workers (CHERP's `user_profiles.role` CHECK
constraint rejects `worker` so "Worker" labels map to `journeyman`).

Results log: `agent_mode/livetest/results.jsonl` — one compact JSON line
per completed round with id, mode, teamCode, duration, ops pass/fail,
team A/B passes, trainer verdict first line. Readable via
`GET /api/livetest/results`.

### Patch Plan generator

`POST /api/livetest/patch-plan` reads the latest (or specified) round,
formats Team B findings + operation log + trainer decision + companion
proposal, and pipes to `claude -p` asking for structured markdown with
fixed sections: Round summary / Issues (severity + evidence) / Proposed
fixes (target / change / test / risk / confidence) / Deploy gate.

Saves to `agent_mode/livetest/patches/<roundId>.md`. Deck button "Patch
Plan" opens a full modal with Copy-to-clipboard. The loop is Live Test →
Team B finds issues → Patch Plan drafts fixes → Ken tests → deploy.

### Auto Mode closed loop

Deck button "Auto Mode: ON/OFF" drives a 90s tick on the frontend:
1. Run Queue — executes queued tasks via `orch.executeTask` (cap 10)
2. Auto Review — calls `claude -p` on waiting_for_claude tasks (cap 6).
   Pipes the prompt via stdin, parses first-line APPROVE/REJECT, calls
   `orch.reviewTask`.
3. If queue is thin (<4 in flight), calls `POST /api/auto/generate-tasks`
   which asks Claude for N new dispatchable tasks as JSON, createTask
   each. Task types, agent roster, and last 8 tasks are all included in
   the prompt so Claude proposes non-duplicate work.

Single-flight guard prevents overlapping ticks. Persists to localStorage.
Drained 14 real pending tasks in one run during this session with 0
errors (6 approve / 8 reject). Claude correctly caught hallucinated
React Native code from cherp-piper and generic templates from llama3.1,
approved a concrete CSV export from qwen2.5-coder.

### System control surface

- **Volume sliders** — `.claude/bin/volume.ps1` inline C# COM interop with
  IAudioEndpointVolume (master) + IAudioSessionManager2 +
  ISimpleAudioVolume (per-process). GET + POST `/api/volume` with
  `{target: 'system'|'app', value: 0..1, app?: 'Spotify'}`. Deck now-
  playing card has two sliders (SYS + SPT) that debounce input 120ms.
- **Now-playing transport** — SMTC via `.claude/bin/smtc-control.ps1` for
  play/pause/toggle/next/prev. Works with Spotify desktop + any SMTC-
  aware app.
- **Wallpaper-matched theme** — `.claude/bin/wallpaper-colors.ps1` reads
  TranscodedWallpaper (Wallpaper Engine aware), grid-samples 48x48 via
  System.Drawing.Bitmap, filters near-gray (sat > 0.28), picks 2 most-
  saturated with 30° hue separation, brightens to fixed HSL luminance.
  `applyWallpaperColors` sets `--sw-magenta/-rgb`, `--sw-cyan/-rgb`,
  `--sw-lavender/-rgb`, `--sw-bg-0/1/2`, `--sw-shell-0/1` CSS vars so
  body gradient + shell bg + every accent retints. Default theme.
- **AFK mode** — real OS-level keypress macro via
  `[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')`. Deck button
  toggles a 5s tick that POSTs `/api/macro/send`. Fires into whatever
  Windows window has foreground focus. Whitelisted keys only.
- **Shell tab on deck** — full PowerShell terminal in the deck Shell
  tab. `POST /api/shell/run` with 30s timeout + 4MB buffer. Bare
  `claude <text>` auto-wraps to `claude -p "<text>"` on the server so
  the shell feels like a Claude REPL.

### Tailscale + Remote clients

- **Tailscale mesh** (`heskeny@` account):
    - `desktop-ed797oh` (dev box) → `100.117.92.46`
    - `laptop-nonc1i8l` (HP laptop) → `100.108.152.63`
  Lets the laptop + phone hit the Pipe-R server from any network
  (home, hotspot, work) without port-forwarding. Windows firewall rule
  "Node.js JavaScript Runtime" already allows inbound 7777 on
  Private+Public. `tailscale file cp <file> <peer>:` moves files between
  machines. `/dl/<filename>` route on the server serves files from
  `input/` as a fallback when Taildrop drops them into an inbox.
- **HP Remote v3** at `clients/hp-remote/` — standalone HTML client
  (no build) with 5 tabs: CLAUDE (prompt box), SHELL (terminal), DECK
  (embeds `pipe-r.html?deck=1` in iframe), METRICS (same), STEAM (same).
  Live wallpaper color sync so the laptop tints exactly like the main
  deck. Points at `http://100.117.92.46:7777` via the Tailscale IP.
  Distributed as `hp-remote-v3.zip` on Ken's Desktop. Includes
  `check-deps.ps1` that detects Tailscale + offers winget install of
  Node.js / Claude Code CLI.
- **PipeR-Remote-Android** (`C:\Users\Ken\Desktop\PipeR-Remote-Android\`)
  — Kotlin + Compose + WebView wrapper pointing at the full ops deck via
  Tailscale IP. App label "Pipe-R v3", v3.0.0. URL configurable via
  Settings FAB. Error overlay with Tailscale-specific diagnostic hints.
- **CHERP-Android** (`C:\Users\Ken\Desktop\CHERP-Android\`) — identical
  WebView template pointing at `https://cherp.live/demo.html`. App label
  "CHERP", applicationId `com.hesken.cherp`. Both Android projects
  install side-by-side without collision.

## Known gotchas learned this session

- **`crew_tasks.id`** is `BIGINT GENERATED ALWAYS AS IDENTITY`. Never send a client id in the POST body. Use `Prefer: return=representation` and read the id back.
- **`daily_logs`** has NO `team_code` column — uses `company_id` + `created_by` (UUID). Cleanup has to track row ids.
- **`messages`** has NO `team_code` either — uses `sender_id` (UUID) + `channel`. `body` is the content column, not `content`.
- **`crew_timecards`** uses client-gen TEXT `id` (not auto). Columns: `user_id`, `user_name`, `hours`, `date` (not `worker_name`/`hours_worked`).
- **`user_profiles`** role CHECK constraint only allows `('apprentice','journeyman','foreman','superintendent','admin','superuser')`. `worker` is NOT valid (still unfixed on live — flagged in CHERP CLAUDE.md).
- **Ollama run spinner leak:** any new ollama spawn path must strip ANSI CSI `\u001b\[\??[0-9;]*[a-zA-Z]` and OSC `\u001b\][^\u0007]*\u0007` from stdout, or chat-log.jsonl will contain terminal noise.
- **CSS :has() specificity** with `.stack:last-child` beats `body[data-deck-tab="..."] .stack` — when overriding deck-mode stack styles per tab, use `!important` on `display` + `flex-direction` + `grid-template-rows`.

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

### CHERP ownership migration (LIVE on cherp.live, 2026-04-13)

Shipping the plan in `.claude/plans/cherp-ownership-system.md` — moving CHERP from team_code-scoped to individual ownership + explicit sharing + offline-first. Emergency backup at `C:/Users/Ken/Desktop/cherp emergency.zip` (commit d9aac2d).

**Phase 1 ✅ — `js/store.js`** (CHERP `dev` branch, commit 79c4c65)
- IndexedDB-backed read-through cache + write-through queue wrapping `SB()`
- Object stores: `rows` ([table,id] key), `queue` (autoinc), `meta` (sync timestamps)
- Public API: `store.list/get/create/update/delete/syncNow/onSync/pendingCount/isOnline`
- 30s stale threshold, 5-retry cap, temp-id → server-id swap on create flush
- Zero existing screens touched — opt-in per-screen migration starts phase 3
- Wired into `demo.html` after `utils.js`

**Phase 2 ✅ — additive schema migration** (CHERP `dev` branch, commit 89656be; applied to Supabase live 2026-04-13)
- `user_profiles.role` CHECK expanded: +`worker`, +`general_foreman` (fixes the known signup 400)
- `user_profiles.employee_id` UNIQUE (nullable) + `reports_to` self-FK with depth chain
- Nullable `owner_id` UUID on: `crew_tasks`, `crew_timecards`, `jsa_reports`, `mro_equipment`, `daily_logs`, `certifications`, `messages`
- New tables: `item_shares` (first-class sharing graph), `notifications` (approval chain + share invites + conflict alerts), `pending_users` (placeholder rows before signup), `edit_conflicts` (concurrent edit escalation log)
- All RLS-scoped to owner/recipient/loser. Migration file: `workspace/CHERP/migrations/2026-04-13_ownership_phase2.sql`
- Verified live via REST: `item_shares` returns `[]`, `user_profiles.employee_id`+`reports_to` columns present

**Phase 2b ✅ — crew_jsa + crew_mros owner_id** (applied live 2026-04-13). Follow-up because the app writes to `crew_jsa`/`crew_mros` not `jsa_reports`/`mro_equipment`. File: `migrations/2026-04-13_ownership_phase2b_crew_tables.sql`.

**Phase 3 ✅ — `tasks.js` → store.js** (dev d11fb71 → main 17b5f96)
- loadTasks/saveTask/toggleTask/deleteTask/cycleTaskProgress/addTaskNote all route through `window.store` with direct-SB() fallback
- New tasks stamp `owner_id: _s.id`
- Temp id → server bigint swap via background syncNow after create
- Supervisor/cross-crew reads stay on SB() (store equality-filter doesn't fit ranges)

**Phase 4 ✅ — `timeclock.js` hot path → store.js** (dev 8891fa9 → main 17b5f96)
- clockIn/clockOut/loadActiveClockIn/loadTodayEntries through store
- Offline clock-in works end-to-end (row visible locally the instant the button fires)
- owner_id stamped on new timecards

**Phase 5 ✅ — safety/work/certifications → store.js** (dev ffd189e → main 17b5f96)
- `safety.js`: saveDraftJSA + sendJSA (deterministic id upsert via `resolution=merge-duplicates`)
- `work.js`: loadMROs/submitMRO/updateMROStatus
- `certifications.js`: submitCert/approveCert/rejectCert
- owner_id stamped on every new row
- `store.js` remoteCreate now uses `Prefer: resolution=merge-duplicates,return=representation` so retries + client-id upserts are idempotent

**Phase 6a ✅ — employee_id foundation** (dev 00e3768 → main 17b5f96)
- `generateEmployeeId(name)` → `XX-#####` format (2 initials + 5 digits)
- `claimEmployeeId(userId, name)` — PATCH helper with 3-retry on UNIQUE violation
- Both signup paths stamp `employee_id` at create
- `launchApp` backfills existing users missing an ID (skips hardcoded su-/adm-* accounts)
- Home screen header shows the ID strip (tappable)
- `showEmployeeIdCard()` modal: big read-out + copy-to-clipboard + scan button
- `scanEmployeeId()` → `lookupAndAddEmployeeId()` flow: validates format, looks up target in `user_profiles`, previews name/role/company
- **Critical fix**: `_s.id = auth.userId` now set at login. Before phase 6a, `_s.id` was never populated, so every phase 3/4/5 `owner_id: _s.id` stamp was writing `undefined` on live. Tests passed only because the harness set `_s.id` manually. This fix is why the merge was load-bearing.

**Phase 6b ✅ — BarcodeDetector QR scanner** (dev df99af4 → main 17b5f96)
- `openQRScanner()` full-screen camera overlay, native BarcodeDetector `qr_code` detection per animation frame, environment-facing camera
- Chrome 88+/Android primary; Firefox/Safari fall back to typed prompt
- `lookupAndAddEmployeeId()` accepts bare IDs or URL-style payloads (`cherp.live/add/KD-04829`)
- No external deps — native browser API

**Test harness** (dev e4085de → main 17b5f96)
- `test/store-smoke-lib.js`: in-memory IndexedDB shim + recording fake fetch (PostgREST emulator)
- `test/store-smoke.js`: 29 assertions on store.js public API
- `test/screens-smoke.js`: 32 assertions loading store + tasks + timeclock in a VM sandbox
- `test/run-all.js`: single entry point
- Run: `node test/run-all.js` — currently 61/61 green
- No deps, pure Node built-ins + vm

**Phase 7+ queued** (not yet built)
- Phase 7: `chat.js` / `messages.js` → employee-id-based 1:1 DMs + shared-item comment threads
- Phase 8: `home.js` + `mycrew.js` fully on the share graph
- Phase 9: Full offline (service worker precache + rolling-window IDB)
- Phase 10: Drop `team_codes` + `crew_members` (optional, HIGH risk)
- Phase 4.5: Nest backend adapter (parallel-option swap, see `memory/project_nest_backend_adapter.md`)

**Phase 4.5 — future Nest backend adapter**
- Plan stub added 2026-04-13. Add a `NEST()` backend to `store.js` as a parallel option, selected per-instance. Pilot customers (JSBackyard, REVV) ship on Nest-backed instances from day one. Supabase stays as dev/test default. Full rationale in `memory/project_nest_backend_adapter.md`. Do NOT start this until phase 3 proves the store abstraction.

**Resolved ownership decisions (Ken 2026-04-13):**
- Workers own their tasks, share with each other explicitly
- Foremen see tasks of workers beneath them via `reports_to` recursive CTE (depth cap 5)
- Teams/crews stay as a layered feature (not core), team_code survives as legacy metadata
- Last-write-wins default, concurrent-edit escalates to owner via `edit_conflicts` + notification
- Notes field is append-merge so two offline editors merge cleanly
- 30-day grace before orphan cleanup after user delete
- 12 simulated conflict tests in plan (SIM-1..12): 10 fully seamless, 2 partial (concurrent edit escalates, IDB corruption uses atomic tx)

### CHERP known schema gotchas (read before touching DB code)

- **`crew_tasks.id`** is `BIGINT GENERATED ALWAYS AS IDENTITY`. Never send client id in POST; use `Prefer: return=representation`
- **`daily_logs`** has NO `team_code` — uses `company_id` + `created_by` UUID
- **`messages`** has NO `team_code` — uses `sender_id` UUID + `channel`. Content column is `body` not `content`
- **`crew_timecards`** uses client-gen TEXT `id`. Columns: `user_id`, `user_name`, `hours`, `date`
- **`user_profiles.role`** CHECK constraint — as of phase 2, `worker` and `general_foreman` are now valid (previously rejected with 400)

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
