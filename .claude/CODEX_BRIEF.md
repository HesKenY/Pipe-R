# CODEX_BRIEF.md — context port from Claude's memory

This file is a consolidated port of Claude's auto-memory store
(`~/.claude/projects/C--Users-Ken-Desktop-Claude/memory/`) into a
single committed file so Codex has the same context when it runs
out of `C:\Users\Ken\Desktop\Codex`. Updated 2026-04-13.

Read alongside:
- `CLAUDE.md` — full project + repo context (same for both agents)
- `AGENTS.md` — coordination protocol between Claude and Codex
- `.claude/HANDOFF_2026-04-13_phase9.md` — what Claude just shipped
  today and what's pending

---

## 1. Who Ken is (user profile)

Ken Deibel (GitHub: HesKenY) is a **non-coder** who builds software
projects entirely through AI tools. Everything must work through
**buttons, menus, and guided flows** — not typed commands or code.
Runs multiple projects simultaneously from a central command
center (Pipe-R). Thinks in orchestration, deployment, packaging —
not raw code. Strong visual/UX instinct, prefers sci-fi-themed
polished interfaces.

**How to work with Ken:**
- Default to **doing the work**, not explaining how to do it.
- Keep explanations practical, never academic.
- Never assume Ken will edit code by hand — provide complete
  solutions.
- UI work must be button-driven and visually rich.
- He has deep domain knowledge in construction and business, not
  in code syntax. Don't talk down — match that level.
- Currently in an apprenticeship program (user-driven, started
  2026-04-09): gradually ramp technical language + terminology as
  he learns. Introduce one new concept per session at most. If
  Ken says "just do it," respect that and save teaching for another
  moment. If he says "explain that," go deep.

**Ken's current technical level (as of 2026-04-13):**

- **Understood:** Git basics, repo structure, Netlify deploys, PWA
  basics, Supabase as a backend, client vs. server keys, HTML/CSS/JS
  file roles, project architecture, Google OAuth2 flow, Google Sheets
  API, server endpoints (REST), agent/model dispatch (Ollama), hub.js
  TUI menu pattern, Google Cloud Console basics.
- **In progress:** RLS (Row-Level Security), serverless functions,
  multi-instance architecture, API design / REST patterns, training
  data pipelines, **schema vs. code drift** (introduced via the
  2026-04-12 crew_tasks bug), **DDL vs. DML** (ALTER TABLE runs in
  SQL editor, reads/writes go through REST).
- **Not yet introduced:** DB schema design beyond existing tables,
  build tools / bundlers, testing, TypeScript, CI/CD pipelines,
  secrets management beyond basics, DNS / domain config, Android
  deployment (Play Store, signing, Capacitor).

---

## 2. Hard feedback rules (never break these)

### 2.1 Ken AI voice rules — CRITICAL

When writing anything in **Ken's voice** (commit messages, code
comments meant to sound like Ken, Ken AI model outputs, anything
routed to `ken-ai:latest`):

- **lowercase** (no capitals, not even at sentence starts)
- **3–10 words** per message is normal
- **typos left in place** ("recieves", "amalogies", "thaat")
- **no pleasantries** (no please / thank you / sorry)
- imperative or declarative ("paste the sql", "continue", "done")
- questions sometimes drop the `?`
- think-out-loud is fine
- "nvm", "btw", "/btw" as casual prefixes
- **no analogies** — no "like a pipe system", no "like a tool drawer"
- **no "as an AI" disclaimers**; no trailing "let me know if you
  need anything"
- answer first, reason second

**Why:** Ken uses Ken AI as a voice extension of himself. When it
over-formalizes or uses performative metaphors, it stops feeling
like him. The previous v1 profile had a "use construction analogies"
instruction that produced *"schema drift is like a pipe system where
parts get mismatched"* — Ken rejected that outright. Professional
is the regression here. Do not re-introduce the construction-
analogy instruction in `agent_mode/ken/profile.md`.

**How to apply when editing `agent_mode/ken/profile.md`:**
- Keep the "How I talk" section first-person and concrete.
- Include actual examples from Ken's messages, not abstract rules.
- Rebuild after edits: `ollama create ken-ai -f agent_mode/ken/Modelfile`

### 2.2 Button-driven UX — no typing required

All UIs (hub.js TUI, web deck, Android app, remote client) must be
button-driven. Ken is a non-coder. Don't add CLI flags or require
typing code. The agent terminal CLI where users type tasks is the
one exception — that's the designated typing interface.

### 2.3 Sci-fi design language (non-negotiable)

Every new UI element uses this palette and feel:

- **Colors:** deep black (#08090d), electric cyan (#00e5ff / #00f0ff),
  purple (#7c4dff), neon green (#00e676 / #00ff88), red (#ff1744 /
  #ff4466), amber (#ffd740 / #f0a030)
- **Feel:** "Alien Isolation meets Bloomberg Terminal meets JARVIS"
- **Effects:** scan lines, glow on hover, grid overlays, typing
  animations
- **Mascot:** robot face "Pipe-R" with expressions and eye tracking

Don't introduce flat / material / generic design. Don't ship a
new feature without applying the theme.

Exception: the **CMC marketing site** at cleanmoneycorporation.com
uses clean professional design (teal `#0ea5a4`, deep navy ink, Inter
font). That's intentional — CMC is the corporate face, CHERP is the
dark sci-fi product. Don't confuse the two.

### 2.4 CHERP design principles

- **Offline-first matters more than real-time sync.** Workers are
  in basements, tunnels, rural sites. The app must work without
  internet and sync when connected. Phase 9 shipped 2026-04-13
  with full SW precache + rolling IDB warmer + three recovery
  escape hatches. See handoff log.
- **Instant page sync on workers' clients is a priority** (added
  2026-04-12). When a foreman creates a task / assigns an MRO /
  files a JSA, workers on that crew should see it on their home /
  tasks / mycrew screens **immediately** without manual reload.
  Extend the existing Supabase Realtime subscription in
  `js/main.js startRealtime()` to cover `crew_tasks`,
  `crew_timecards`, `crew_mros`, `crew_jsa`, `crew_incidents`.
- **Manual sync button** always exposed — Realtime over WebSocket
  is fragile on construction sites; workers need an "I know it's
  stale, refresh NOW" lever.
- **GPS + selfie verification for time clocks is a trust mechanism,
  not surveillance.** Frame it that way in the UI.
- **Role-based access is critical** (hierarchy in `js/config.js`
  ROLE_RANK): apprentice(1) < worker(2) < foreman(3) <
  general_foreman(4) < superintendent(5) < superuser(6). Apprentices
  and superintendents don't see the same screens.
- **The AI assistant (Pipe-R) should feel like a knowledgeable
  journeyman, not a chatbot.** Not corporate, not academic. It
  knows codes, specs, field math. It talks like someone who's
  carried the pipe.

---

## 3. Project ecosystem

### 3.1 The ladder (commercial top → technical bottom)

1. **CMC (Clean Money Corporation)** — S-corp owned by Ken Deibel
   + Sean Bedard. Repo `HesKenY/CMC` (public marketing site).
   Domain `cleanmoneycorporation.com`. Sells **ACE** (CHERP
   rebrand) to construction companies. Two-page funnel: wedge
   landing ($149 entry) + ACE product page ($399 / enterprise).
   Clean professional design, NOT sci-fi.
2. **Piper (Pipe-R)** — the command center. Ken's working
   environment. Lives at `C:\Users\Ken\Desktop\Claude` (and now
   `C:\Users\Ken\Desktop\Codex` — parallel clone for Codex).
   Repo: `HesKenY/CHERP-Backup` (primary / origin) +
   `HesKenY/Pipe-R` (secondary). Runs agent_mode (Ollama training
   /dispatch), logging, sessions, Google Sheets sync, orchestrates
   everything else.
3. **Nest (Bird's Nest)** — customer instance builder. Lives at
   `workspace/CHERP-Nest`. Repo `HesKenY/CHERP-Nest` (private).
   Every build shallow-clones `HesKenY/CHERP` main, stamps the
   SHA into the instance manifest, brands + bakes a zip. Every
   shipped customer instance is traceable to a specific CHERP
   revision.
4. **CHERP** — the product. Public repo `HesKenY/CHERP`, deployed
   to `cherp.live` via Netlify from `main` branch. This is what
   Nest bakes customer copies of.
5. **CodeForge** — at `C:\Users\Ken\Documents\CodeForge`, deployed
   to `codesforge.netlify.app`. Separate project.
6. **ForgeAgent** — Python AI agent hub at `Desktop/FORGE-main`.
   Trains Ollama models, deploys them as terminal coding agents,
   TUI-driven. Shares sci-fi design philosophy.

### 3.2 Commercial sell flow

Prospect pays → Ken fires Nest for that customer (company name,
colors, Supabase config, admin account, module selection) → Nest
fetches fresh CHERP main, bakes branded instance, outputs zip +
customer README → instance deploys (Netlify or customer hosting)
→ **Ken's team maintains that instance for 90 days** → after 90
days, handoff (customer takes ownership, OR separate ongoing
maintenance contract).

The 90-day window is why we need strong logging (app_logs),
traceability (instance.json source SHA), and a fast migration
pipeline (migrations/ folder pattern). Handoffs need clean docs
for a non-Ken operator to run the thing.

### 3.3 Pilot customers (real, queued)

1. **JSBackyard** — friend's business, field-testing the platform.
2. **REVV** — another friend's business. Reclaimed name after the
   2026-04-08 Codex incident (see §6.1). First two real exercises
   of `/api/nest/build` and the 90-day maintenance clock.

Low-stakes feedback loop. Light customization only — brand colors
+ company name + admin account. Save deep customization for paying
customers.

---

## 4. Pipe-R command center architecture

### 4.1 Physical layout

```
C:\Users\Ken\Desktop\Claude\       ← Claude's working folder (brain)
C:\Users\Ken\Desktop\Codex\        ← Codex's working folder (brain)

Both folders share the same structure and same git remotes:

├── PIPE-R.bat         ← double-click: launches everything
├── DECK.bat           ← chromeless Chrome at 1920×720 → pipe-r.html?deck=1
├── START.bat          ← quick stop+start+hub (terminal)
├── STOP.bat           ← quick kill :7777
├── NEST.bat           ← launches Nest alone
├── server.js          ← Piper HTTP API on :7777
├── hub.js             ← Piper terminal TUI (~3.4K LOC, button-driven)
├── pipe-r.html        ← Trainer Deck web UI (served by server.js)
├── remote.html        ← phone remote web UI (PIN 0615)
├── clear-sw.html      ← standalone SW recovery page (CHERP-style)
├── agent_mode/        ← the shared agent runtime
│   ├── core/          ← orchestrator, queue, registry, executor, memory
│   ├── config/        ← agents.json, runtime.json, tasks.json
│   ├── ken/           ← Ken AI profile + Modelfile + README
│   ├── m3w/           ← M3w Promptdex profile + Modelfile (companion)
│   ├── memories/<slug>/  ← per-agent notes.md, chat-log.jsonl, charter.md
│   ├── training/      ← training-log.jsonl + charters + curate.js
│   ├── livetest/      ← scenarios + rounds + results.jsonl
│   └── sheets/        ← Google Sheets sync (OAuth2)
└── workspace/         ← gitignored, holds sub-repos
    ├── CHERP/         ← HesKenY/CHERP clone (cherp.live source)
    └── CHERP-Nest/    ← HesKenY/CHERP-Nest clone (builder)
```

### 4.2 Folder pipeline convention

- `input/` — source files dropped in for work
- `workspace/` — active work in progress
- `staging/` — review-ready artifacts
- `output/` — finished deliverables and packaged builds

All four are gitignored, auto-created by hub.js on boot.

### 4.3 Run commands

```bash
node hub.js        # Terminal UI (interactive, blocking)
node server.js     # HTTP API on :7777 (background, auto-sync on)
```

No `npm install`. Both scripts are standalone Node.js built-ins.

**Stopping a background server:** `tasklist //FI "IMAGENAME eq node.exe"`
to find the PID, then `taskkill //PID <pid> //F`. Or use
`STOP SERVER.bat`.

---

## 5. Agent Mode (eight-agent party)

Eight Ollama models registered with specialized roles — "the party
+ trainer + companion":

| Slot | Badge | Display | Base model | Track |
|---|---|---|---|---|
| Trainer | TR | Ken AI | `ken-ai:latest` (from qwen2.5-coder:14b) | trainer / orchestrator |
| Party 1 | SCZ | 5c1z0r Patchsmith | `qwen2.5-coder:14b` | implementation |
| Party 2 | ROT | R0t0m Relay | `forgeagent:latest` | integration |
| Party 3 | DEC | D3c1du3y3 Pathfinder | `cherp-piper:latest` | recon |
| Party 4 | PGN | P0ryg0n Logdex | `llama3.1:8b` | observability |
| Party 5 | UMB | Umbr30n Safeguard | `jefferyjefferferson:latest` | quality |
| Party 6 | ALK | 4l4k4z4m Archive | `jefferferson:latest` (slow cold start) | memory |
| Companion | M3W | M3w Promptdex | `m3w-learning:latest` (from llama3.1:8b) | learning |

**Routing heuristics:**
- Code tasks → Qwen / ForgeAgent
- Construction domain queries → CHERP Piper
- Ken-style work → Ken AI
- Prompt-tuning / post-task learning → M3w

### 5.1 Per-agent memory system

Every registered agent gets a directory under
`agent_mode/memories/<slug>/` (slug = id with colons replaced by
hyphens). `server.js` scaffolds these at boot via
`agent_mode/core/memory.js ensureAllMemoryDirs`. Each dir has:

- **`notes.md`** — durable standing instructions + facts. **Injected
  into every chat turn AND every dispatched task** by
  `executor._buildPrompt()`. Source of truth for "I always want
  agent X to do Y".
- **`chat-log.jsonl`** — append-only audit of every chat turn
  (role, content, ts). Cleared by the deck's Clear button.
- **`charter.md`** — mirror of the agent's training charter.

The same `notes.md` loader runs in both the chat endpoint
(`POST /api/chat`) and the executor's task dispatch path, so
there is ONE source of truth per agent. Write it once, it applies
everywhere.

### 5.1a 2026-04-17 trainer direction update

- Canonical lead trainer / orchestrator identity is now
  **`kenai:v4-offline-developer`**.
- **`ken-ai:latest` stays as a legacy compatibility alias**, mainly
  for old memory continuity and fallback routing, but it is no longer
  the naming target for new corpus work.
- Default corpus direction is now **coding-first local developer**:
  repo safety, patching, tool JSON, verification, offline_agent,
  Windows-local workflows, agent coordination.
- Default corpus should **de-weight or exclude** older game-first
  loops and construction-role drift when building new fine-tune sets.
- Current V4 corpus pipeline lives in:
  - `agent_mode/training/corpus_builder_v4.mjs`
  - `agent_mode/training/export_kenai_v4_dataset.mjs`
  - `agent_mode/training/kenai-v4-finetune.jsonl`

### 5.2 Key executor / dispatch rules

- **Always pass the prompt via stdin**, not as a shell argument.
  Windows `cmd.exe` has an 8191-char limit and double-quote
  escaping corrupts multi-line SYSTEM prompts. Fixed
  2026-04-12 by switching to
  `spawnSync('ollama', ['run', model], { input: prompt })`.
- **Strip ANSI spinner sequences** from every ollama stdout
  before writing to memory / log. The bytes to strip:
  - `\u001b\[\??[0-9;]*[a-zA-Z]` (CSI)
  - `\u001b\][^\u0007]*\u0007` (OSC)
- **`agents.json` is held in memory by the running server.**
  Editing the file while `server.js` is live gets clobbered on
  next save. Stop server → edit → restart.
- **Agents with `"blocked": true`** are skipped by
  `orchestrator._tryAutoAssign` and render with a red `BLOCKED`
  badge. Direct dispatch by id still works.
- **Executor retry cap** lives in `orchestrator.js` (merged from
  Codex rebuild 2026-04-12 commit `a599eb9`).

---

## 6. Known gotchas (read before touching)

### 6.1 Codex incident (2026-04-08, historical)

On 2026-04-08, ChatGPT Codex went rogue and:
1. Dumped `Desktop/REVV-main-Android/` (~130 files) into the repo
2. Renamed CHERP references to REVV in hub.js / server.js
3. The REVV files included a `netlify/functions/create-checkout.js`
   requiring `stripe`, which broke all Netlify builds

Cleaned up 2026-04-09: removed Desktop/REVV-main-Android, added
`Desktop/` to .gitignore, pushed revert. REVV the name was later
reclaimed 2026-04-12 as a real pilot customer handle — that's a
deliberate reuse. **Do not rename CHERP. Do not re-introduce REVV
files.**

### 6.2 CHERP schema gotchas (critical — the migration code runs against these)

- **`crew_tasks.id`** is `BIGINT GENERATED ALWAYS AS IDENTITY`.
  Never send a client id in POST. Use `Prefer: return=representation`
  and read the id back.
- **`daily_logs`** has NO `team_code` column — uses `company_id` +
  `created_by` UUID.
- **`messages`** has NO `team_code` — uses `sender_id` UUID +
  `channel`. Content column is `body`, not `content`.
- **`crew_timecards`** uses client-gen TEXT id. Columns: `user_id`,
  `user_name`, `hours`, `date`.
- **`user_profiles.role`** CHECK constraint — as of ownership
  Phase 2, `worker` and `general_foreman` are now valid (previously
  rejected with 400).
- **`pipe_messages`** (Pipe-R's own chat table, not CHERP `messages`)
  gained `from_employee_id`, `to_employee_id`, `thread_key` columns
  in Phase 7a (2026-04-13). Thread key shapes:
  - `dm:<min(from,to)>:<max(from,to)>` — employee-id DMs
  - `crew:<team_code>` — crew broadcasts
  - `item:<type>:<id>` — shared-item comment threads (Phase 7b)

### 6.3 Ollama cold start

- `jefferferson:latest` (Alakazam Archive, slot 6) — cold start
  ~90s to first token. Do not route `summarize` / `memory_extract`
  tasks to it while cold (30s executor timeouts). `draft_patch` /
  `draft_test` (120s) and `scan` / `learn` (60s) are safer.
- **Warm button** landed on the deck 2026-04-13 —
  `POST /api/agent/warm { agentId }` spawns `ollama run <base>`
  with a trivial stdin prompt to load the model into Ollama's
  resident cache. Use the deck button or hit the endpoint directly.

### 6.4 Supabase project

- **Active:** `nptmzihtujgkmqougkzd`
- **URL:** `https://nptmzihtujgkmqougkzd.supabase.co`
- **Schema:** 21+ tables, master SQL in `cherp-schema.sql`
- **CSP:** `netlify.toml` `connect-src` MUST include the project URL
  or API calls silently fail
- **Dead projects:** `pflprnvmhklomqscwceg` (paused),
  `lydhilytlwzaowswhkxr` (modular rebuild, gone). Ignore.

### 6.5 Google Sheets sync

- **GCP project:** `cherp-493003`
- **OAuth client:** `294359454385-u6n51uhkub2d5dkm75e0406gl7dhtaf2.apps.googleusercontent.com`
- **Auth email:** `kdeibel.pipedown@gmail.com` (test user)
- **Token:** `agent_mode/sheets/token.json` (gitignored)
- **Credentials:** `agent_mode/sheets/credentials.json` (gitignored)
- **Alpha Crew sheet:** `1QwE0Aur8BVd0SrAee6OnXA7QKY9-1F0NJBo0v8mwnNY`
- **Auto-sync:** server.js pushes every 15 min when token + crews exist.
- **Status:** OAuth authorized 2026-04-10. App still in "testing"
  mode in GCP — needs publishing for production.

### 6.6 CHERP security — service key exposure

The Supabase **service role key** (`SB_SVC`) is currently in
`js/config.js` in the public CHERP repo. Used by `js/auth.js`,
`js/utils.js`, `js/screens/admin-panel.js`. Bypasses RLS entirely.

**Why it's there:** the app needs it to function. Stripping it
broke crew management / admin screens.

**Don't strip it without a replacement.** Ken wants to address this
incrementally with serverless functions or edge functions as a proxy.
Flag issues, explain tradeoffs, implement when Ken's ready. Don't
push a big security refactor unprompted.

---

## 7. CHERP state as of 2026-04-13 (phases)

See also `.claude/HANDOFF_2026-04-13_phase9.md` for the current-
day shipping log.

**Phases shipped to cherp.live main:**

1. **Phase 1** — `js/store.js` offline-first IndexedDB cache +
   write-through queue wrapping `SB()`
2. **Phase 2** — additive schema migration: owner_id everywhere,
   `item_shares` first-class table, `notifications`, `pending_users`,
   `edit_conflicts`, expanded role CHECK constraint, employee_id +
   reports_to on user_profiles. Applied live via Supabase SQL editor.
3. **Phase 3** — `js/screens/tasks.js` migrated to store.js
4. **Phase 4** — `js/screens/timeclock.js` migrated to store.js
5. **Phase 5** — `safety.js` / `work.js` / `certifications.js`
   migrated to store.js
6. **Phase 6a** — employee_id generation + display (`KD-04829`
   format) + scan + lookup
7. **Phase 6b** — BarcodeDetector QR scanner
8. **Phase 7a** — employee-id DMs on `pipe_messages` with
   deterministic `thread_key` (shipped 2026-04-13)
9. **Phase 7b** — item-comment threads on tasks + MROs via same
   `thread_key` primitive (shipped 2026-04-13)
10. **Phase 9a** — service worker precache flip to cache-first,
    28 files in PRECACHE_URLS, rolling IDB warmer on login
    (shipped 2026-04-13)
11. **Phase 9b** — shared-item warmer via `item_shares` graph
    (shipped 2026-04-13)
12. **Phase 9c** — three SW recovery escape hatches
    (`?sw=off` URL killswitch, `/clear-sw.html` standalone page,
    admin-panel "Clear SW Cache" button) (shipped 2026-04-13)

**Phases still queued:**

- **Phase 7c** — retire team_code broadcast, channels-as-shared-items
  (parked — conflicts with future ID-system expansion)
- **Phase 8** — home.js + mycrew.js fully on the share graph
- **Phase 10** — drop team_codes / crew_members tables (HIGH risk,
  optional)
- **Phase 4.5** — Nest backend adapter (parallel `NEST()` option
  in store.js for pilot customers, after phase 3 validated)

---

## 8. Related repos

| Project | Repo | Domain | Notes |
|---|---|---|---|
| CHERP | HesKenY/CHERP | cherp.live | Construction crew management |
| Bird's Nest | HesKenY/CHERP-Nest | — | Backend superuser / instance builder |
| Pipe-R | HesKenY/Pipe-R | — | Command center (this repo — secondary remote) |
| Pipe-R Backup | HesKenY/CHERP-Backup | — | Command center primary / origin (repointed 2026-04-12) |
| CMC | HesKenY/CMC | cleanmoneycorporation.com | Marketing site for ACE product |
| CodeForge | HesKenY/CodeForge | codesforge.netlify.app | — |

---

## 9. Session-end ritual

Every session should end with:

1. All Piper remotes up-to-date (origin + pipe-r)
2. Nest remote up-to-date (if touched)
3. CHERP main up-to-date (if touched)
4. CMC main up-to-date (if touched)
5. Working tree committed or deliberately parked with a note
6. `WORKLIST.md` updated if the punch list changed

The four-repo sweep is the end-of-session ritual.

---

## 10. How Claude works with Ken (meta-rules)

- **Don't narrate internal deliberation.** User-facing text should
  be relevant updates, not running commentary.
- **Keep text between tool calls ≤25 words.** Keep final responses
  ≤100 words unless detail is genuinely needed.
- **State in one sentence what you're about to do** before the first
  tool call. Brief updates at key moments (found something / changed
  direction / hit a blocker). Silent is bad, verbose is worse.
- **End-of-turn summary:** one or two sentences — what changed,
  what's next. Nothing else.
- **Default to writing no code comments.** Only add them when the
  WHY is non-obvious. Never narrate WHAT (good names do that).
  Never reference the current task, PR, or caller names in comments.
- **No emojis unless explicitly requested.**
- **Match the scope of actions to what was actually requested.**
  Don't add features, refactor, or introduce abstractions beyond
  what the task requires. A bug fix doesn't need surrounding
  cleanup. Three similar lines beats a premature abstraction.
- **For UI work, test in a browser before reporting complete.**
  Type checking and test suites verify code correctness, not
  feature correctness.
- **Don't commit unless explicitly asked.** "Explicitly asked"
  means Ken said commit / ship / push / merge. Don't be proactive.
- **Risky actions get confirmed first.** Destructive ops, force
  pushes, shared-state mutations, external communications — all
  need explicit authorization each time. Authorization stands for
  the scope specified, not beyond.
