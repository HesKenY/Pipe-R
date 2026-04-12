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
