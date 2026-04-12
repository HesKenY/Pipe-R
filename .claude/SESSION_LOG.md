# Session Log

Date: 2026-04-12 (continuing 2026-04-10/11 session)

## 2026-04-12 (late) — What Was Done

### CHERP — schema drift bug hunt + fix sweep
Ken surfaced a set of field-testing bugs via 14 screenshots from cherp.live.
Root-caused each one against the live Supabase via REST probes, then shipped
schema migrations + code patches. All five bugs closed in one session.

- **Bug 1 — crew_tasks 400 on save:** `tasks.js` was writing `work_type,
  photo_b64, done_at, progress, due_date` but none of those columns existed
  on `crew_tasks`. Migration
  `migrations/2026-04-12_crew_tasks_add_missing_cols.sql` adds them. Verified
  with a real POST against Supabase REST, including a payload with a base64
  photo and `assigned_to` set. Task create + PATCH reassign both green.
- **Bug 2 — team_codes 400 on Create Crew:** `crews.js saveCrew()` was
  writing `foreman_phone, sb_url, sb_key, active` — none on the live table.
  Same migration adds them. Superuser "Create New Crew" now works.
- **Bug 3 — crew_members duplicate rows:** 9 rows for ALPHA-01, 5 of which
  were duplicate Ken-Deibel foreman rows (no unique constraint, every join
  stacked a new row). Migration dedupes by
  `row_number() OVER (PARTITION BY team_code, device_id)` and adds the
  `crew_members_unique_device UNIQUE (team_code, device_id)` constraint so
  future joins collapse via `Prefer: resolution=merge-duplicates`.
- **Bug 4a — crew_timecards table didn't exist at all:** timeclock.js does
  10+ queries against `crew_timecards` (clock in/out, weekly summary, CSV
  export, foreman corrections). The table was never created — PGRST205 404
  on every call. New migration
  `migrations/2026-04-12_create_crew_timecards.sql` creates it with 16
  columns, 5 indexes, and permissive RLS policies matching the sibling
  crew_* tables. Live-tested POST clock-in + PATCH clock-out + DELETE.
- **Bug 4b — api.open-meteo.com blocked by CSP:** `netlify.toml` connect-src
  only allowed self, Supabase, and formsubmit.co. home.js + work.js both
  fetch from api.open-meteo.com for weather — silently dying at the CSP
  layer. Added to the allowlist.
- **Bug 5 — Superuser seeing "Join a Crew" prompt + getting added to
  crew_members:** four guards applied per workspace/CHERP/CLAUDE.md spec
  (home.js prompt hide, main.js registerMember early-return, crews.js
  joinCrew toast+return, crews.js joinCrewSilent hard-return). Schema seed
  updated to stop inserting Ken as Superuser into crew_members on fresh DB
  builds. Live crew_members table cleaned: deleted both Ken Deibel rows
  (seed superuser row + stale foreman row left over from before the guards
  were deployed).
- **Logo consistency:** demo.html, admin.html, landing.html were still on
  the older `assets/logo.webp`. index.html, signup.html, and manifest.json
  were on the newer `assets/cherp-icon-192.png`. Unified everything on the
  PNG icon so the logo is consistent across auth screen, top bar, admin,
  favicon, and iOS home-screen install.
- **jheath foreman account:** created in Supabase `user_profiles` (PIN
  1234, role=foreman, crew=ALPHA-01) and pre-seeded into `crew_members` so
  he appears in the crew list before first login.

**CHERP main commits shipped:**
- `c44a941` Fix schema drift: crew_tasks, team_codes, crew_members
- `1ebb1e1` Fix time clock: create crew_timecards, allow open-meteo in CSP
- `cc1bd76` Guard superuser from crew-join flow
- `127c879` Stop seeding Ken Deibel (superuser) into crew_members
- `7983fd8` Standardize logo to cherp-icon-192.png everywhere

**ALPHA-01 live state after cleanup:** 4 crew members — S. Bedard,
C. Deibel, N. Deibel (Superintendents from seed), J. Heath (Foreman,
freshly seeded). No Ken, no duplicates, no superuser entries.

### Ken AI — BUILT
- `ollama create ken-ai -f agent_mode/ken/Modelfile` completed cleanly
- Model ID `326ad05d282a`, 9 GB, based on qwen2.5-coder:14b
- Smoke test: `echo "Say hello in one sentence." | ollama run ken-ai:latest`
  returned "Hello!" — model loads, profile SYSTEM prompt is active
- `agent_mode/config/agents.json` flipped from `status: pending_build` to
  `status: idle` with `builtAt: 2026-04-12T06:05:00Z`. Orchestrator can
  now dispatch to ken-ai.

### Pipe-R agent mode
- Confirmed server.js running (2 node PIDs, sheets/status alive, 30s
  auto-exec loop ticking, 15-min auto-sync ticking)
- Queue state reviewed: 6 tasks stuck in `waiting_for_claude` from
  2026-04-10/11 with bad outputs (cherp-piper was routed to code-scan
  tasks but it's a plumbing-domain fine-tune — answers in IPC codes
  instead of scanning code). 1 task correctly `failed`
  (`task-mnscqowp-jz6f`, jefferferson). Nothing new queued this session.

### Memory
- `user_learning.md` — added "schema vs code drift" and "DDL vs DML" as
  concepts introduced 2026-04-12 via the crew_tasks bug. Added a
  2026-04-12 session note about Ken using "continuity" correctly and
  independently prioritizing the field-bug fix before continuing Ken AI.

### Pipe-R — agent mode dispatch bug fixed
Discovered during the Ken AI smoke test: every orchestrator dispatch
was producing garbage outputs regardless of which agent was picked.
Three combined bugs:

1. `queue.js add()` hardcoded `assignedAgent: null`, silently dropping
   the agent parameter from /api/dispatch.
2. `orchestrator.js createTask()` didn't forward `opts.assignedAgent`
   to `queue.add()`, so `_tryAutoAssign()` always ran and routed to
   whatever the auto-assigner preferred.
3. `executor.js` used `execSync` with the prompt passed as a quoted
   shell arg. Windows cmd.exe has an 8191-char limit and double-quote
   escaping corrupts multi-line SYSTEM prompts — Ken's 6 KB profile
   was arriving at the model as shell noise. This is why cherp-piper
   kept answering every task like a plumbing inspector regardless of
   the objective.

Fixed in Pipe-R commit `02d0d6f`:
- queue.js honors opts.assignedAgent
- orchestrator.js passes it through
- executor.js switched to `spawnSync('ollama', ['run', model], { input: prompt })`
  so the prompt goes through stdin — no length limit, no shell escaping

After `STOP SERVER.bat` + `START SESSION.bat`, verified end-to-end:
dispatch with `agent: "ken-ai:latest"` correctly routes and produces
real Ken-voice output on the first try. All 6 legacy stuck tasks from
earlier this week are still in `waiting_for_claude` — they should
either be re-dispatched now that the executor works or closed out.

### Pipe-R — Ken AI v1 voice rewrite (drop plumber analogies)
First run of Ken AI via the fixed dispatch produced polished
metaphorical outputs like *"schema drift is like a poorly maintained
plumbing system where pipes become misaligned."* Ken rejected it:

  "i want ken-ai to respond as if its me, not in plumber amalogies"
  "i want ken-aai to have the same tone and speak the same way i
   speak to you"

Two sources of truth were out of sync:
- `profile.md` (loaded as executor prompt prefix)
- `Modelfile` SYSTEM block (baked into the Ollama model at create time)

The Modelfile had its OWN copy of the instructions — including the
"use construction analogies" line — and `ollama create` was reusing
cached layers, so profile.md edits alone didn't change the baked
SYSTEM prompt. Rewrote BOTH with Ken's actual typed voice (lowercase,
3–10 words, typos left in, no pleasantries, no analogies, no trailing
summaries, answer-first-reason-second) and included literal examples
from this session's messages as anchors. Rebuilt → new layer hash
`aa07f11c74497f310abb5e25e6695e8c9f4ed0175bfc0cb326db3b4afd90a0cc`.

Verification dispatches:
- Q: "why is schema drift dangerous?"
  A: "schema drift is dangerous because the code writes columns the
      db doesnt have. every insert 400s. silent data loss."
- Q: "service workers or indexeddb for cherp offline?"
  A: "service workers are better for caching assets and handling fetch
      requests. [...] for cherp, service workers provide a more robust
      offline experience with less code changes needed."

Lowercase, no analogies, direct, typo `doesnt` preserved. Voice is at
about 80% — still a touch more polished than Ken's real keyboard tone,
will tighten as training-log.jsonl accumulates real Ken-in-the-loop
responses.

Feedback memory saved at `memory/feedback_ken_ai_voice.md` so the
rule survives future profile rewrites. MEMORY.md index updated.

### CHERP — user_profiles drift fix + superuser viewing-crew refactor
Ken's first field test after the earlier fixes hit two more bugs: the
Manage tab was empty, and superuser still saw "Join a Crew to Get
Started" even though the guard had shipped. Root-caused to user_profiles
schema drift: JS reads/writes `team_code` in ~15 places but the live
table only had a legacy `crew` column, so every user_profiles select
that enumerated team_code was 400'ing.

Fixed in two layers:
- **Code-side drift resilience** (commit `fe7778d`): every SELECT
  switched to `select=*`, every filter switched from `team_code=eq.`
  to `crew=eq.`, every write to `crew` instead of `team_code`. Auth
  launchApp() normalizes `profile.team_code ||= profile.crew`.
- **Schema migration** (`2026-04-12_user_profiles_team_code.sql`): adds
  `team_code` + `foreman_id` columns, backfills from `crew`, and
  installs a bidirectional BEFORE INSERT/UPDATE trigger so legacy
  `crew` writers and modern `team_code` writers stay in sync.

Also in `fe7778d`, a real architectural fix for the superuser vs. team
system conflict that's been dogging us all night:

**Viewing-crew context.** Superusers don't have a real crew membership,
but every query in the app is scoped by `_s.teamCode`. Instead of
refactoring 100+ call sites, superusers get a "viewing crew" populated
into `_s.teamCode` at login time (last-viewed from localStorage or
first active crew). All existing code "just works" because the filter
now sees a real crew code. The join guards already shipped prevent
superusers from ever being written into `crew_members` during normal
flows — so there's permission-to-view without membership-in-fact.

UI piece: new purple **"👁 CODE ▾"** button in the top bar, visible
only for `_s.isSU`. Opens a crew switcher modal listing every crew,
with the active one marked. `switchCrew(code)` updates `_s.teamCode`,
persists the choice to localStorage, re-renders the current screen.

Plus a theorycraft writeup (feedback given, not saved as memory yet)
explaining the difference between **permission** (master key, lives
in RLS policies, lets superuser SEE everything) and **context** (the
currently-viewed crew, lives in the session, controls what you're
asking about at any given moment). Both pieces are needed; neither
alone is enough. The memory-worthy part is that the fix belongs on
the client, not in a magic wildcard `team_code`.

### CHERP — 8 missing-table audit + migration
Full schema audit of the JS revealed 10 tables referenced in code
that don't exist in live Supabase. Two were in-memory-only
(`notifications`, `crew_specs`) — false alarms. The remaining **8
are actually missing** and every feature touching them has been
silently dead since launch:

| JS expects | Status |
|---|---|
| `pipe_messages` | missing — chat, broadcast, realtime subscriptions dead |
| `crew_mros` | missing — material requests dead |
| `crew_jsa` | missing — Safety tab JSAs dead |
| `crew_jsa_signatures` | missing — JSA sign-offs dead |
| `crew_cos` | missing — change orders dead |
| `worker_certifications` | missing — cert uploads dead |
| `crew_incidents` | missing — near-miss / injury reports dead |
| `app_logs` | missing — every `log()` call silently fails, no audit trail |

Legacy tables `jsa_reports`, `change_orders`, `certifications`,
`messages` exist in the DB but with completely different shapes (UUID
FKs vs. name-based, different columns). Can't be renamed — they're
from a half-completed schema refactor and aren't what the app writes
to. Migration only creates new tables, leaves legacy in place.

Migration file `migrations/2026-04-12_missing_app_tables.sql` adds all
8. Column shapes reverse-engineered from actual INSERT/PATCH/SELECT
call sites in `js/screens/` and `js/main.js`. Conservative — anything
missed can be added via `ALTER TABLE ADD COLUMN` follow-up, same
pattern we used for `crew_tasks` earlier in the night.

Post-migration verification: all 8 tables return HTTP 200 on
`SELECT *`. Live POST tests on the 4 highest-impact ones
(`pipe_messages`, `crew_mros`, `crew_jsa`, `crew_cos`) all returned
201 with realistic JS-shaped payloads. Cleanup DELETEs returned 204.

Commit `b8a7f84` on CHERP main.

### CHERP — logo standardization + jheath account
Side-quests during the main bug hunt:
- **Logo consistency** (`7983fd8`): `demo.html`, `admin.html`,
  `landing.html` were still using `assets/logo.webp`. Standardized
  everything on `assets/cherp-icon-192.png` — matches `index.html`,
  `signup.html`, and `manifest.json` which were already on the newer
  icon. Top bar, auth screen, admin panel, and iOS home-screen icon
  all consistent now.
- **jheath foreman account**: created `J. Heath` / PIN 1234 / role
  foreman / crew ALPHA-01 via REST. Written to both `user_profiles`
  (crew column) and pre-seeded into `crew_members` so the row
  appears in the crew list before first login. Paired with deleting
  both Ken Deibel rows from `crew_members` (seed superuser row + stale
  foreman row from before the guards deployed) and updating the
  `cherp-schema.sql` seed to stop inserting superusers into crew_members
  on fresh DB builds (commit `127c879`).

### CHERP main commits shipped this session (full list)
- `c44a941` Fix schema drift: crew_tasks, team_codes, crew_members
- `1ebb1e1` Fix time clock: create crew_timecards, allow open-meteo in CSP
- `cc1bd76` Guard superuser from crew-join flow
- `127c879` Stop seeding Ken Deibel (superuser) into crew_members
- `7983fd8` Standardize logo to cherp-icon-192.png everywhere
- `fe7778d` Superuser viewing-crew context + user_profiles drift resilience
- `b8a7f84` Migration: create 8 missing app tables

### Pipe-R local commits (not pushed to remote)
- `915b272` Session 2026-04-11/12: Ken AI v1 built, CHERP bug sweep, Sheets sync live
- `02d0d6f` Fix agent mode dispatch: honor assignedAgent, pipe prompt via stdin
- `d1a7bb8` ken-ai: rewrite voice — respond AS Ken, not as a plumber narrator

## Still-open items for next session
- **Verify the fixes live** — log in to cherp.live as `jheath` / `1234`,
  create a task with a photo, assign it to a worker, clock in/out, check
  the crew list shows no duplicates and no superuser entries. Browser
  test that the SQL + code fixes hold under real use.
- **schema vs code drift inventory** — user_profiles.team_code is
  referenced in crews.js:571 but doesn't exist on the live table. Same
  class of bug as the ones fixed today. Worth a sweep: grep every SB()
  call for field names and cross-check against live schema. Could queue
  this to ken-ai once he's wired into the orchestrator.
- **Queue state cleanup** — 6 stuck tasks in `waiting_for_claude` with
  junk outputs should either be reviewed+closed or re-routed to qwen /
  ken-ai. Don't let the queue accumulate rot.
- **Executor retry cap** — still no max-retries in `orchestrator.js`
  (open item from yesterday's session). Jefferferson's 82-retry loop
  is the cautionary tale.
- **Landing page destination** (from yesterday's open decisions):
  cherp.live/foremen vs subdomain vs new domain — still blocked on Ken.

## 2026-04-11/12 — What Was Done

### Pipe-R / infrastructure
- MCP server auth: Vercel authenticated; Gmail and Calendar queued for /mcp UI
- Killed stuck task `task-mnscqowp-jz6f` (jefferferson retry loop, 82 retries no backoff). Marked failed in tasks.json. Server restarted clean.
- Ken AI v1 scaffold shipped at `agent_mode/ken/`: profile.md, Modelfile, README.md
- Wired `ken-coder` personality into `agent_mode/core/executor.js` (loads profile.md fresh at startup)
- Registered Ken AI as agent #7 in `agents.json` with `status: pending_build`
- Updated `CLAUDE.md` with Ken AI section, Known Issues subsection, background server pattern, new Future items
- Created Desktop scripts folder `C:\Users\Ken\Desktop\Pipe-R Scripts\` with 6 .bat files + README
- Created Codex rebuild brief folder `C:\Users\Ken\Desktop\Pipe-R Rebuild (Codex)\` with 7 numbered files (00-06) + empty workspace, paranoid rules from REVV incident

### CHERP company strategy work
- ACE Strategy doc shipped: `CHERP - ACE Strategy.html` + .pdf on Desktop. Three-letter framework (Audit/Connect/Exit) with competitor matrix, integration priorities, M&A landscape, 90-day execution plan
- Pricing Model v1.0 shipped: `CHERP - Pricing Model and Analysis.html` + .pdf on Desktop. Four-tier model (Free/Crew/Pro/Nest) with unit economics and revenue scenarios
- Pricing Model v1.1 shipped: added Own-It perpetual-license tier as 4th paid option. Reframed as "five-tier, four paid options". Fair-market pricing $2,499/$4,999/$9,999 derived from 2.5-3.5x SaaS multiple research
- Procore + Raken integration brainstorm notes: `CHERP - Procore Raken Integration Notes.md` on Desktop. Real API details, 10 brainstorm plays tagged Must/Should/Could, 5 founder decision points
- Master Worklist: `CHERP - Master Worklist.md` on Desktop. Single source of truth merging ACE 90-day plan, integration plays, Pipe-R backlog. Five sections (executable, decisions blocked, founder actions, engineering backlog, Pipe-R side)
- Wedge landing page draft: `CHERP - Wedge Landing Page DRAFT.html` on Desktop. Sci-fi dark theme, foreman audience, comparison table vs Procore/Fieldwire/Raken, dual CTA (free trial / Own-It)

### CHERP code spikes (in `workspace/CHERP`, gitignored, not pushed)
- Weather auto-capture spike: `js/screens/safety.js` — added `fetchWeatherForJSA()`, weather badge in JSA form, `weather_snapshot` field on save. Needs `CHERP_OPENWEATHER_KEY` in `js/config.js` and `crew_jsa.weather_snapshot JSONB` schema column to ship
- Raken CSV migration parser: `migrations/raken-import.js` — standalone Node script, parses Raken time-card CSV exports, dry-run mode + JSON stdout for Supabase POST piping. Handles common Raken column variants

### Ken's co-founder
- Sean Bedard added as co-founder on all CHERP company documents (ACE Strategy, Pricing Model, Worklist, Integration Notes)

## Today's Priority Order — STILL OPEN
1. **Ken AI** — model is scaffolded, awaits `ollama create ken-ai -f agent_mode/ken/Modelfile` to actually build
2. **Website version with local storage** — personal Google integration, offline-capable
3. **Android multi-instance architecture** — Hub routing, Play Store onboarding
4. **CHERP web Sheets button** — finish sheet_url column + mycrew.js button
5. **Nest wizard Google Cloud steps** — auto-provision Sheets per instance
6. **CHERP home screen auto-refresh/sync** — live-update when Supabase/Sheets data changes
7. **Nest dependency install hook** — Node.js check + permission prompt + install in wizard flow

## Open Decisions Blocking Work (from Master Worklist Section 2)
- 2.1: Ken builds Procore integration himself, or hires a developer?
- 2.2: Treat Raken as partner, competitor, or ignore?
- 2.3: Own-It with Procore pre-wired option ($5,999), yes/no?
- 2.4: Procore marketplace listing now, wait for first customer, or just informational call?
- 2.5: First target pilot customer archetype — regional MEP, union MEP, regional GC, or franchise?
- 2.6: Landing page hosting destination — `cherp.live/foremen`, subdomain, or new domain?

## What Was Done — Earlier (2026-04-10)
- Google Sheets Sync: auth.js, schema.js, sync.js — full push/pull engine, zero deps
- Hub.js [G] menu, server.js 4 endpoints + 15-min auto-sync timer
- Google OAuth authorized (project cherp-493003, account kdeibel.pipedown@gmail.com)
- Alpha Crew spreadsheet created and synced live
- CLAUDE.md updated with Sheets docs + Future section
- Pipe-R pushed to GitHub (43fea8f, 34d38c7)
- Created user account: thall / 1234 / journeyman / ALPHA-01
- Icon modernization across all CHERP screens (9 files, 6 icon swaps)
- CHERP pushed to GitHub

## Tomorrow — Priority Order
1. **Ken AI** — personality coding model, frame using agent_mode training pipeline
2. **Website version with local storage** — personal Google integration, offline-capable
3. **Android multi-instance architecture** — Hub routing, Play Store onboarding
4. **CHERP web Sheets button** — finish sheet_url column + mycrew.js button
5. **Nest wizard Google Cloud steps** — auto-provision Sheets per instance
6. **CHERP home screen auto-refresh/sync** — live-update when Supabase/Sheets data changes (no manual reload)
7. **Nest dependency install hook** — during program generation, check for required deps (Node.js first); if missing, prompt user for permission and auto-install

## Architecture Notes for Tomorrow

### Website Version — Local Storage + Personal Google
Ken wants a version of CHERP that runs with local storage (browser-side) and personal Google account integration. The idea: a lightweight personal version where your data lives in YOUR Google Sheets/Drive, not in a company Supabase instance. Could serve as:
- Personal work diary / timecard tracker
- Individual tool that syncs to company instance when connected
- Standalone mode for independent contractors
Think: PWA with localStorage + Google Sheets as the "database"

### Android Multi-Instance Network
When a company buys CHERP, Nest provisions their own Supabase instance. Workers download ONE universal app from Play Store, enter a team code, and get routed to the correct company instance.

**Central Hub** (one Supabase project):
- `instance_registry` table: team_code → supabase_url, anon_key, company_name
- Read-only for the app, zero user data stored
- Only cross-instance connection point

**Flow:** Download app → enter team code → Hub lookup → connect to company instance → create account there

**Security:** Instances never talk to each other. Hub only maps codes to URLs. RLS handles everything within instances.

**Open questions:**
- Hub = existing project or new dedicated one?
- One code per crew or one per company?
- Cache instance URL permanently or re-check?
- Worker switching companies?
- Google Sheets provisioning per-instance via Nest?

### Nest Wizard — Google Cloud Integration
When Nest builds a new CHERP instance, it should also:
- Create Google Spreadsheet set for that company
- Set up OAuth credentials for Sheets sync
- Store sheet URLs in instance's team_codes
- Register team codes in the Hub routing table
