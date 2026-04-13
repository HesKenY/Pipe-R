# CHERP — Ownership System

Morning plan 2026-04-13. Pending Ken approval before any code changes.
Emergency backup already captured at `~/Desktop/cherp emergency.zip`.

## Direction lock-in (Ken 2026-04-13)

- **Offline-first is THE anchor.** Every screen must function against
  the local device store first, sync to remote second. No screen
  should hit Supabase on the main thread of a user action.
- **Ownership system** is the name of the whole architecture. Data is
  owned by the individual who created it.
- **Sharing is explicit**, not broadcast. Two paths:
    1. Direct share to a specific person via employee ID
    2. Role hierarchy (`reports_to` chain) — a foreman automatically
       sees items owned by workers under them, a general foreman sees
       foremen + workers under them, etc.
- **Teams / crews are a LAYERED feature**, not legacy, not core.
  Stay fully supported as an optional organizational unit on top of
  individual ownership. Groups come later as a priority push.
- **Employee IDs** (the previously-named "friend codes") are the
  public user identity. Format `KD-4829`. QR scan, direct typing,
  invite flow all work through them. Sibling plan:
  `.claude/plans/employee-id-qr-rollout.md`.
- **Manage tab** is the supervisor workspace where a foreman checks
  tasks + progress of workers under them, edits worker info, approves
  timecards. Manage tab is driven by the role hierarchy visibility.
- `team_codes` + `crew_members` tables stay as active org metadata.
  No drops.

## Theorycraft — issues to solve before we build

Read this first. Every item is a design trap I want Ken's sign-off on
before I write code that commits to an answer. Organized by category.

### A. Data model + ownership semantics

1. **Who owns an assigned task — creator or assignee?**
   Current plan: creator owns, assignee sees it via either (a) implicit
   auto-share or (b) the reports_to hierarchy. Problem: if a foreman
   creates a task and assigns it to a non-reporting contractor,
   neither mechanism surfaces it. Proposal: on task create with
   `assigned_to_user_id`, also write an implicit `item_shares` row
   (`owner_id=creator, shared_with=assignee, can_edit=true`). The
   share auto-revokes if the assignee changes.

2. **Multiple assignees on one task.** Current schema has
   `assigned_to TEXT` singular. Construction reality: "Two guys on
   the wall, Mike and Jose." Options: (a) keep singular, make "assign
   to crew" a create-N-tasks macro instead, (b) many-to-many via a
   `task_assignees` junction table, (c) JSON array column. Ugliest
   but most flexible: (b). Simplest: (a). Recommendation (a) —
   matches how Ken says tasks work in the field.

3. **Assigning to someone who hasn't signed up yet.** Foreman creates
   a task for "New Guy" who doesn't have a user_profile row. Options:
   (a) reject, force signup first, (b) allow a text-only assignee and
   link retroactively when the row appears, (c) create a placeholder
   profile. Recommendation (a) — require real user first, matches
   the ownership story.

4. **Company-owned assets (MRO tools, shared certifications).** A
   drill belongs to the company, not a person. Options: (a) virtual
   "Company" user_profile row that owns all shared assets, (b) new
   `owner_org_id` column, (c) null owner_id + explicit "company
   scope" boolean. Recommendation (a) — simplest, reuses the
   `item_shares` table for "check out to worker X", doesn't bloat
   schema. The demo superuser row already exists and can serve.

5. **Historical orphans.** After backfilling `owner_id` by matching
   `display_name`, rows where the creator's display_name no longer
   exists get null. Options: (a) leave null, surface in admin "claim"
   UI, (b) auto-assign to nearest active superintendent, (c) delete.
   Recommendation (a) — never destroy data, let admin resolve.

### B. Role hierarchy + reports_to

1. **Recursive depth.** `reports_to` chain lookup needs a `WHERE
   depth < 5` guard to avoid infinite loops from bad data. Real
   construction hierarchies are 3-4 levels deep (apprentice →
   journeyman → foreman → GF → superintendent). 5 is the safety cap.

2. **Orphan foreman.** Foreman leaves the company. Their row gets
   deactivated (`is_active = false`). Every worker with
   `reports_to = <deleted foreman>` becomes invisible to upstream
   supervisors because the chain breaks. Fix: ON DELETE SET NULL +
   a "reports_to_backup" or nightly re-parent job. Recommendation:
   when a foreman deactivates, auto-reassign their direct reports to
   the foreman's own supervisor (chain walk up by one). Triggered
   via admin action, not automatic.

3. **Multi-foreman workers.** Journeyman works for foreman A on
   Mondays and foreman B on Tuesdays. Single `reports_to` column
   can't express that. Options: (a) many-to-many via `supervisors`
   junction table, (b) primary + "loaned to" tag, (c) use crews —
   worker is in crew A + crew B, each crew has a foreman, visibility
   walks crew membership instead of reports_to. Recommendation (c)
   is the cleanest — lets us fold crews back into the hierarchy
   story without parallel plumbing.

4. **Role upgrades mid-employment.** Apprentice → journeyman →
   foreman. Existing tasks stay owned by them; their `reports_to`
   starts getting populated by new hires. Upward visibility works
   instantly. One-directional promotion is clean.

5. **Role downgrades.** Foreman demoted to journeyman. They still
   have workers with `reports_to` pointing at them. Options: (a)
   auto-reassign to their own supervisor (chain walks up), (b) block
   demotion until manual reassignment, (c) leave dangling and hide
   them from those workers' chain. Recommendation (a) with an
   audit-log warning, because (b) blocks legitimate demotions behind
   admin paperwork.

6. **Circular references.** Data-integrity trap. Two users somehow
   get reports_to pointing at each other. Recursive CTE loops until
   the depth guard kicks in. Fix: CHECK constraint or trigger on
   user_profiles UPDATE that walks up 5 levels and errors if it ever
   returns to the starting id.

7. **"GF sees all foremen under them" via recursive CTE cost.** For
   a 200-user company this is a millisecond query. For 10,000-user
   enterprise it starts to matter. Not a problem for CHERP's current
   scale but worth noting in case of growth — at scale the pattern
   is a materialized `reporting_chain UUID[]` column updated by a
   trigger.

### C. Offline-first conflict scenarios

1. **Two foremen both editing the same shared task offline.** Both
   come online, sync in order, second write clobbers first. Losing
   foreman sees their edit gone with no warning. Fix: on client
   sync, detect remote `updated_at > local.synced_at` and surface a
   banner + keep losing edits in `store_audit` local table.
   Acceptable because scalar-field conflicts are rare; the common
   case is additive (notes, photos) which we append-merge.

2. **Append-merge for task notes.** `crew_tasks.notes` is already a
   JSON array of `{text, by, at}`. Two users add notes offline —
   merge by concatenating both arrays and sorting by `at`. Safe.

3. **Worker clocked in offline, supervisor looks at phone, sees old
   state.** Supervisor's local cache doesn't know yet. Fix: the
   clock-in banner shows "as of <timestamp>, device online/offline",
   and the store has a 30s stale-read policy that silently
   background-refreshes on tab focus.

4. **Same user signing in on two devices offline.** Edits diverge.
   Store needs a per-install device ID (not per-user) so conflict
   detection knows "this edit came from device X, this other edit
   from device Y." Generate via `crypto.randomUUID()` on first run,
   store in localStorage. Device ID gets written into every edit as
   an audit field.

5. **Service worker cache staleness.** Phone opens app offline, sees
   cached app shell from before a schema change, tries to write to
   an `owner_id` column that was removed in a later version, store
   errors. Fix: bump `CACHE_VERSION` constant on every deploy that
   changes the store schema, service worker hard-refreshes on
   version mismatch.

6. **IndexedDB quota exhaustion.** 5 GB per origin on Chrome Android.
   A year of tasks + photo blobs could blow it. Retention policy:
   keep the full current 30 days + only completed/closed items for
   prior 11 months, then summarize + evict. Photos are the heavyweight
   — consider offloading to Supabase Storage lazily on upload instead
   of keeping the b64 locally forever.

### D. Employee ID collisions + security

1. **Initials collision blow-up.** "KD-" prefix only has 10k codes.
   Two Ken Dawsons in a 500-person company is realistic; a third
   makes the retry loop slow. Fix: widen suffix to 5 digits (100k
   codes per pair) OR abandon initials for pure random
   alphanumerics. Recommendation: 2 letters + 5 digits (`KD-04829`),
   still sayable, 676 * 100,000 = 67.6M space.

2. **Enumeration attack.** Knowing the format, an attacker brutes the
   whole space. 10k options at 1 req/sec = 3 hours; 100k = 28 hours.
   Mitigation: (a) rate limit employee-id lookups per IP, (b) require
   auth to query, (c) server-side the invite flow so the recipient
   never sees the sender's raw ID until they accept. Recommendation:
   all three. An unauthenticated "who is KD-4829" lookup is
   unnecessary.

3. **Invite spam.** Malicious foreman sends 1000 invites per minute
   to every employee ID they can guess. Rate limit: 50 invites per
   foreman per 24h hard cap, 5 per minute soft cap. Recipients can
   block a sender to kill future invites from them.

4. **Employee leaves, ID retirement.** Retire permanently, never
   recycle. Old tasks + history stay attached. Reactivation brings
   the same ID back.

5. **Typo scenario.** Foreman mistypes `KD-4829` as `KD-4928` and
   sends an invite to the wrong person. They get an invite from a
   stranger, decline. No harm. But warn on send: "Send invite to
   KD-4928 (Maria Gonzales)?" — show the recipient name in a
   confirmation so the foreman catches the typo. Needs a lookup
   endpoint that returns display_name for an employee_id, gated to
   foreman+ role.

### E. Crews as layered feature friction

1. **Dual visibility rules**: "I can see this task because I own it"
   vs "I can see this task because I'm on the same crew as the
   owner" vs "I can see this task because I'm the owner's foreman".
   Three overlapping rules will confuse users. Fix: every item card
   shows a small "Why can I see this?" chip — `MINE`, `SHARED BY X`,
   `CREW Y`, `REPORTS TO ME`. Makes mental model visible.

2. **Zero-crew users.** Legacy code assumes `_s.teamCode` is always
   set. Breaking assumption. Audit: grep every `_s.teamCode`
   reference and make them nullable-safe. Phases 1 + 2 cover this.

3. **Multi-crew users.** Schema already allows it (multiple
   crew_members rows). Old screens assumed 1:1. Audit: every place
   that reads `_s.teamCode` as "my crew" needs to become "my crews"
   (plural). Probably 15-20 call sites.

4. **Multi-crew foreman.** A foreman owns 3 crews. Their Manage tab
   needs a crew picker at the top. Keep it simple: tabs or dropdown.

5. **Crew chat vs 1:1 chat.** After migration, chat has two shapes:
   1:1 DM by employee ID and crew channel. The crew channel is a
   shared item owned by the foreman, auto-shared with every crew
   member. Sends are broadcast into the shared channel, not per-
   recipient. Works without new primitives.

### F. Manage tab (supervisor workspace)

1. **Scope control.** Foreman's Manage tab shows workers where
   `reports_to = me OR (worker is in a crew where I'm foreman)`.
   GF's Manage tab shows everyone who reports to anyone who reports
   to me, recursively. Capped at 5 levels.

2. **Approval UX for timecards.** Current flow: foreman sees all
   timecards for their team_code. New flow: foreman sees timecards
   where the owner is downstream (reports_to chain). Approval
   action sets `approved: true, approved_by: <foreman_id>,
   approved_at: <now>`. Worker's share of the timecard auto-
   elevates can_edit to false after approval so they can't
   retroactively change hours.

3. **Bulk-edit worker info (Quick Edit).** Already exists in
   `employee-card.js`. Needs downstream gating: GF can edit workers
   in their chain, foreman can edit workers in their chain, both
   can't edit peers or upstream. RLS + client check.

4. **Progress dashboard.** Foreman wants "percent complete" across
   all downstream tasks. Straight query: `count(done=true) /
   count(*)` for tasks where `owner_id IN (my chain)`. Cache the
   rollup in localStorage with 60s TTL so the dashboard is instant.

5. **Task reassignment inside the chain.** Foreman drags a task
   from Worker A to Worker B. Reassignment writes a new
   `assigned_to_user_id`, revokes the old implicit share, creates a
   new one. Audit-logged.

### G. Migration data integrity

1. **Ambiguous display_name backfill.** Multiple user_profiles rows
   with the same display_name means `UPDATE owner_id FROM
   user_profiles WHERE display_name = created_by` picks an arbitrary
   one. Fix: during backfill, if ambiguous, leave owner_id null and
   surface in admin for manual resolution.

2. **Reports_to backfill for existing users.** We don't know who
   reports to whom today. Options: (a) leave null, let superintendent
   manually set via admin UI, (b) infer from team_code + is_foreman
   — if I'm a worker in crew X, I report to the foreman of crew X.
   Recommendation (b) with manual override. Runs once in phase 2,
   never again.

3. **Role CHECK constraint drift.** `user_profiles.role` CHECK
   allows `('apprentice','journeyman','foreman','superintendent','admin','superuser')`
   but `config.js` ROLE_RANK has `worker` and `general_foreman`.
   Flagged in CHERP CLAUDE.md. Fix in phase 2 migration: expand the
   CHECK constraint to include `worker` + `general_foreman`, OR
   drop them from ROLE_RANK. Recommendation: expand the DB
   constraint — ROLE_RANK is the source of truth for UX, the DB
   should match.

### H. Android wrapper / service worker gotchas

1. **WebView IndexedDB persistence.** Android WebView treats each
   installed app as a separate origin. Users who browse to
   cherp.live in Chrome AND install the Android wrapper have two
   separate local stores. Not fixable without deep linking; just
   document it.

2. **Service worker scope.** CHERP's existing service worker
   registers at the root. The wrapper loads `/demo.html` so the
   SW scope is `/`. Should work but needs verification after the
   store ships.

3. **Camera permission timing.** Phase 6 QR scanner asks for camera.
   Needs `WebChromeClient.onPermissionRequest` override in
   MainActivity.kt. Not a blocker, just a rebuild.

4. **Offline install experience.** First launch of the wrapper on a
   fresh phone requires an initial sync to populate IndexedDB. If
   the phone is offline on first run, the app is empty until sync.
   Show a "First sync needed — connect to WiFi" banner.

### I. Pipe-R Live Test Mode impact

1. **WS5A3Q-based scenarios still work in phases 1-5** because
   team_code columns stay. New scenario
   `kitchen-remodel-3day-ownership.json` arrives in phase 6 using
   the ownership flow instead. Team B (Umbr30n QA) grades both.

2. **The patch plan generator already caught the first bug** in the
   v1 runner during the last session. Keep running patch plans
   after every migration phase to catch regressions early.

### J. Deploy + rollback

1. **Netlify auto-deploys main → cherp.live.** A broken commit is
   live in ~30 seconds. Mitigation: every phase lands on `dev`
   branch first, Netlify deploy preview URL smoke-tested in Ken's
   browser, then merged to `main`. No exceptions.

2. **Emergency rollback.** `cherp emergency.zip` is a cold snapshot
   of files. The real rollback is `git revert <commit>` followed by
   push. Supabase schema changes revert via a rollback migration
   that drops the added columns — write it alongside every forward
   migration.

3. **Hotfix path during migration.** If a bug ships during phase 3,
   we need to hotfix it without blocking phase 4. Branches:
   `main` = production, `dev` = integration, `phase-N` = feature
   branch for each phase. Merge phase-N into dev, test, merge dev
   into main when green.

## 0. Decision to make

Current CHERP is built around `team_code` as the primary grouping key:
- `user_profiles.team_code` — which crew you're on
- `team_codes` — the crew itself
- `crew_members` — denormalized member list per crew
- `crew_tasks` — tasks scoped to a team_code
- `crew_timecards` — timecards scoped to a team_code
- `mro_equipment` — gear scoped to a team_code (or company)
- `daily_logs` — logs scoped to a team_code
- `messages` — channels keyed by team_code

**Proposed new model:** everything is tied to the `user_profiles.id`
that created it. Crews become a loose tag — a user can be on multiple
crews or none, and their data belongs to them regardless. Offline-first:
every screen must function against localStorage when the network drops,
and sync back when it returns.

**Friend code / QR system from last night's plan becomes the primary
join mechanism** — not a parallel path. But that's phase 3+; first we
get CHERP working without team_code as the required scope.

---

## 1. Proposed schema (additive, backward-compat first)

**Nothing gets dropped in phase 1.** team_code stays on every table for
now — we just stop requiring it and start writing `owner_id` alongside.
Removal happens in a later phase after every screen has been migrated.

### user_profiles — already has what we need

```sql
-- No changes required in phase 1. Already has id (UUID), display_name,
-- pin_hash, role, team_code (keep), and the new friend_code column from
-- the friend-code plan.
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS friend_code TEXT;          -- see friend-code plan
-- team_code stays nullable, becomes advisory instead of required
```

### crew_tasks → tasks (rename conceptually, keep table name for now)

```sql
ALTER TABLE crew_tasks
  ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;

-- Backfill existing rows: owner = the user whose display_name matches
-- created_by, or null if we can't match.
UPDATE crew_tasks t
SET owner_id = u.id
FROM user_profiles u
WHERE t.owner_id IS NULL
  AND u.display_name = t.created_by;

CREATE INDEX IF NOT EXISTS idx_crew_tasks_owner ON crew_tasks (owner_id);
CREATE INDEX IF NOT EXISTS idx_crew_tasks_assigned ON crew_tasks (assigned_to);
```

Tasks become per-user creations. `assigned_to` already exists as a TEXT
display_name — we can add `assigned_to_user_id UUID` alongside and
backfill it similarly, without removing `assigned_to` until every
screen reads the UUID form.

### crew_members → still exists but becomes a loose tag

Keep the table. Stop treating it as the source of truth. The source of
truth for "who are my teammates" becomes: every user whose `team_code`
overlaps with mine, OR every user I've directly added via friend code
invite, OR nobody.

No schema change here in phase 1.

### crew_timecards, daily_logs, mro_equipment, certifications

Same pattern: add `owner_id UUID REFERENCES user_profiles(id)`,
backfill from an existing name column, leave `team_code` untouched.

```sql
ALTER TABLE crew_timecards     ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;
ALTER TABLE daily_logs         ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;
ALTER TABLE mro_equipment      ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;
ALTER TABLE worker_certifications ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;
-- messages already has sender_id which IS the owner_id — no change needed
```

Indexes on `owner_id` for each. Backfill where possible. For rows that
can't be matched, leave `owner_id` null and let the UI show them as
"orphaned legacy records" in an admin view.

### item_shares — first-class, phase 1

Since sharing is THE collaboration model, this table lands in the
phase 1 migration alongside `owner_id`:

```sql
CREATE TABLE IF NOT EXISTS item_shares (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  item_type   TEXT NOT NULL CHECK (item_type IN ('task','timecard','mro','daily_log','certification','jsa')),
  item_id     TEXT NOT NULL,  -- bigint or uuid, TEXT for cross-table flexibility
  owner_id    UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  shared_with UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  can_edit    BOOLEAN NOT NULL DEFAULT false,
  can_reshare BOOLEAN NOT NULL DEFAULT false,
  message     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_item_shares_shared_with
  ON item_shares (shared_with) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_item_shares_item
  ON item_shares (item_type, item_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_item_shares_owner
  ON item_shares (owner_id) WHERE revoked_at IS NULL;

-- Dedup: never allow the same (type, id, from, to) pair twice active
CREATE UNIQUE INDEX IF NOT EXISTS idx_item_shares_unique_active
  ON item_shares (item_type, item_id, owner_id, shared_with)
  WHERE revoked_at IS NULL;
```

RLS policy: row is SELECTable by `owner_id` or `shared_with`. INSERT
allowed for the owner. UPDATE (to set `revoked_at` or toggle
`can_edit`) allowed for the owner only. Superuser bypasses via service
key.

**What "visible to me" means after this change**:
A user's feed on any screen = rows where `owner_id = me` UNION rows
where there's a non-revoked `item_shares` with `shared_with = me`.
Client-side, the local store materializes both sets into a unified
list sorted by created_at.

**Sharing trigger UX**: every item card has a "Share" button. Tap
it → pick from your contacts list (people whose friend codes you've
accepted) → optional message → OK. The recipient gets a notification,
and the item shows up in their feed with a "Shared by Ken" badge.

---

## 2. Client-side — offline-first architecture

This is the biggest code change. Every screen currently queries Supabase
directly for its data. New pattern:

### Local store (`js/store.js` — new file)

A single module that wraps all CRUD, with three backends:

1. **Local** — IndexedDB (already used partially by CHERP for offline
   queue) keyed by table + owner_id + item id
2. **Remote** — Supabase REST via the existing `SB()` / `SB_Admin()`
   wrappers
3. **Sync engine** — pushes local changes to remote when online, pulls
   remote changes to local on app open

Public API:
```javascript
const store = {
  // Read — always hits local first, returns fast. Kicks a background
  // refresh from remote if online and the local copy is > 30s old.
  async list(table, filter) { ... }
  async get(table, id) { ... }

  // Write — updates local immediately, queues a remote sync. If
  // online, the queue flushes within ~1s. If offline, flushes on
  // reconnect.
  async create(table, row) { ... }
  async update(table, id, patch) { ... }
  async delete(table, id) { ... }

  // Sync — manual trigger + listener
  async syncNow() { ... }
  onSync(listener) { ... }
};
```

Every existing screen migrates from `SB('crew_tasks?...')` to
`store.list('crew_tasks', { owner_id: _s.id })` or similar. Reads are
instant from IndexedDB, writes are instant with background sync.

### Offline queue — upgrade existing

`utils.js queueOffline()` + `flushOfflineQueue()` already exist. We
extend them into the store's sync engine. Existing queue rows stay
compatible — they're a subset of what the store handles.

### Conflict handling

Last-write-wins by default (using `updated_at`). For tasks, the
`notes` field is append-only JSON array so two users updating
different notes merges cleanly. For other fields, remote wins on
conflict because the user's intent was "update this row" and the
remote has the authoritative state.

If a user's offline write was lost due to remote clobber, show a
toast: "Your edit to '<task text>' was overwritten by a newer change.
See the audit log." Keep the lost edit in a `store_audit` table so
they can recover it.

### What screens need changes

| Screen | Change |
|---|---|
| `home.js` | list tasks/messages/timecards for `_s.id` instead of `_s.teamCode` |
| `tasks.js` | tasks are per-user; assigned_to still TEXT for display but add `assigned_to_user_id` to track the real target |
| `timeclock.js` | punch in/out writes `owner_id = _s.id`, team_code optional |
| `crews.js` | "My Crew" becomes "People I work with" — list of users I've invited OR been invited by |
| `safety.js` | JSAs are per-user, can be shared |
| `chat.js` / `messages.js` | channel becomes friend_code-based 1:1 or invite-gated group instead of team_code broadcast |
| `mycrew.js` | list teammates from `item_shares` + accepted invites |
| `admin-panel.js` | super/foreman can still see everyone via service key |

Each screen is a small PR. Sequence below.

### Offline UX — what the user sees

- Top bar shows `● ONLINE` or `○ OFFLINE · 3 pending sync` pill
- Every button works the same way regardless of connectivity
- After 30s offline, a banner: "Working offline. Changes will sync
  when you're back online."
- Pending-sync count clicks open a panel showing exactly what's
  queued, in order, with retry / cancel per row

---

## 3. Rollout phases — offline-first anchored

**Phase order changed from the original draft** — offline-first store
lands FIRST so every subsequent phase is built on solid ground.

| Phase | What ships | Risk | Rollback |
|---|---|---|---|
| **0** | **`cherp emergency.zip` backup** ✅ | None | N/A |
| **1** | `js/store.js` — IndexedDB-backed store with read-through cache, write-through queue, manual `syncNow()`. Transparently wraps existing `SB()` calls for any screen that opts in. NO schema changes yet. | Low — no DB changes, just a new file | Revert file |
| **2** | Schema migration: add `owner_id` everywhere + `item_shares` table + `friend_code` on user_profiles + backfill. All additive. | Low | Drop new columns/table |
| **3** | Migrate `tasks.js` to store — reads from local first, sync on foreground. Tasks owned by creator. Sharing UI prototype. | Medium — user-facing change to the highest-traffic screen | Revert + zip restore |
| **4** | Migrate `timeclock.js` to store + `owner_id`. Offline clock-in works end-to-end. | Medium | Same |
| **5** | Migrate `safety.js` (JSA) + `mro_equipment` + `certifications` to store + `owner_id`. Each gets a Share button. | Medium | Same |
| **6** | Friend-code + QR + invite flow from the sibling plan. Establishes the contact graph that sharing depends on. | Medium | Same |
| **7** | Migrate `chat.js` / `messages.js` to friend-code 1:1 DMs + shared-item comment threads. Retire team_code broadcast channels. | Medium — chat UX change | Same |
| **8** | `home.js` + `mycrew.js` fully on the share graph. "My Crew" = people I have active shares with. Team_code UI hidden. | Medium | Same |
| **9** | Offline Full: service worker precaches the app shell + assets, IndexedDB holds a rolling window of all owned + shared items. Phone can be offline 48+ hours and still function. | Medium — service worker cache is sticky, bugs are hard to evict | Bump cache version in netlify.toml |
| **10** | Optional: drop `team_codes` + `crew_members` tables. Schema cleanup. | High | Restore from Supabase snapshot |

Phases 1-8 can happen without ever removing a column. Ken can stop at
phase 8 and cherp.live works perfectly well with individual ownership
while keeping team_code around as legacy metadata.

Phases 9-10 are optional cleanups that can wait months or indefinitely.

---

## 4. What breaks / what must not break

**Must not break during the migration:**
- Existing logins (PIN + team_code mixed auth)
- Any existing tasks / timecards / MROs / JSAs visible to their
  current owners
- `cherp.live/demo.html` — Netlify auto-deploys from main, so any
  broken commit is live in ~30s. Phase in dev branch first, merge
  to main only after smoke test.
- Pipe-R Live Test Mode's WS5A3Q flow — it uses `team_code`
  extensively. Live Test v2 will need a parallel `friend-code`
  scenario, ship alongside phase 5/6.

**Will break temporarily:**
- Legacy "join by code" UX stays functional but gets harder to find
- Mass-broadcast messages to a whole team_code stop existing after
  phase 5 (replaced by invite-gated group channels)
- The Google Sheets sync assumes per-crew spreadsheets — it stays
  functional but the notion of "per crew" becomes "per the
  foreman/owner who created the data". Spreadsheets become per-user
  instead of per-crew, or per-contract if we add a new grouping
  later.

---

## 5. Pipe-R Live Test Mode — what changes

Current Live Test scenarios (`kitchen-remodel-3day.json`) create a
team_code-scoped crew + tasks. That still works in phases 1-4 because
team_code columns stay.

At phase 6 we add a new scenario:
- `kitchen-remodel-3day-invites.json` — same workload, but the foreman
  adds workers via friend-code invites instead of shared team_code
- Team B (QA) fails the round if any invite doesn't round-trip
- Live Test v1's 6-agent split grades it the same way

Phase 8+ we retire `kitchen-remodel-3day.json` in favor of the
invite-based version as the default.

---

## 6. Android wrapper — what changes

`CHERP-Android` already points at `https://cherp.live/demo.html`.
Every phase lands on Netlify → the Android wrapper picks it up on the
next reload. No rebuild required for phases 1-5.

**Phase 6** (QR scanner) needs the camera permission change documented
in the friend-code plan:
- `AndroidManifest.xml`: `<uses-permission android:name="android.permission.CAMERA" />`
- `MainActivity.kt`: override `WebChromeClient.onPermissionRequest` to
  grant camera to the WebView
- versionCode bump, rebuild APK, sideload

**Phase 7+ (offline-first)** needs no native change — the browser's
IndexedDB + Service Worker already work in WebView. CHERP already has
a service worker; we just extend its caching strategy.

---

## 7. Questions for Ken — decide before phase 1

Resolved by Ken's 2026-04-13 direction lock-in:
- ✅ Offline-first is priority — store lands before schema migration
- ✅ Sharing system, not broadcast — `item_shares` is phase 2
- ✅ `crew_members` + `team_codes` kept as legacy metadata, no drops
  until phase 10 at the earliest

Still open:

1. **Scope of ownership — per-individual or per-company?** Per-individual
   for v1 (every person's data belongs to them, shared explicitly).
   Per-company aggregation can happen in an admin view later by
   walking the share graph. OK?

2. **1:1 DMs vs group channels.** Phase 7 ships 1:1 DMs only. Groups
   can come later as a "share a channel with multiple people at once"
   primitive on top of the same `item_shares` table. OK?

3. **Migration-day risk — Supabase preview branch?** Preview branch
   adds safety at the cost of ~2 min extra setup time. Recommendation
   still: use a preview branch for phase 2. OK?

4. **Conflict resolution strategy for the offline store.**
   Last-write-wins on scalar fields (updated_at), append-merge on
   array fields (task notes, certifications list). On conflict, show
   a banner "X edited this after you — their version kept. See audit
   log for your lost edit." Keep losers in a local `store_audit`
   queue Ken can replay. Acceptable?

5. **Field test timing — start phase 1 now, or wait for today's test
   to pass first?** Recommendation: wait. If the test finds a bug,
   we want to be able to ship a hotfix through the current architecture
   without the offline store half-migrated. Start phase 1 after the
   field test is green.

---

## 8. Estimated effort

| Phase | Estimate |
|---|---|
| 0. Backup | Done (1 min) |
| 1. Schema migration | 1 session — 2 hours |
| 2. Store + sync engine | 1 session — 4 hours |
| 3. tasks.js migration | 1 session — 2 hours |
| 4. timeclock + safety + mro | 1 session — 3 hours |
| 5. chat + messages friend-code channels | 1 session — 3 hours |
| 6. Friend-code + QR system | 1 session — 4 hours |
| 7. home + mycrew + offline-first full | 1 session — 4 hours |
| 8. Hide legacy team_code UI | 1 session — 1 hour |
| 9. Optional schema cleanup | 1 session — 1 hour |
| 10. Optional table drops | (skip unless needed) |

**Total: ~24 hours across 8 sessions**, not counting field-test time.
One week of focused work if you're doing nothing else, two weeks
alongside normal ops.

---

## 9. Approval checkpoints Ken needs to green-light

Before I touch any code, I need yes/no on:

- [ ] Scope of ownership — per-individual or per-company?
- [ ] Messaging model — 1:1 first, groups later? OK?
- [ ] Keep `crew_members` + `team_codes` as legacy metadata? OK?
- [ ] Supabase preview branch for schema testing before prod?
- [ ] Start now or after field test?
- [ ] Partial offline first, then full offline?
- [ ] OK to add IndexedDB as a first-class store layer?
- [ ] Does the friend-code plan from last night still stand, and we
      layer this migration underneath it?

Once those are answered, phase 1 (schema migration) starts. Each phase
after that is a single commit with a smoke test and a field check
before the next one starts.

---

## 10. What I will NOT do without explicit approval

- Drop the `team_codes` table
- Drop the `crew_members` table
- Break the existing PIN + team_code login
- Ship any phase to `main` without a `dev` branch test first
- Touch `workspace/CHERP/js/screens/safety.js` (the ACE Pricing
  weather spike — still deferred)
- Delete any existing user_profiles row
- Run schema changes directly against prod without a preview branch

---

Awaiting go/no-go on the questions in section 7 + the checkpoints in
section 9 before starting phase 1.
