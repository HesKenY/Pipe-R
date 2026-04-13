# CHERP — Offline-first + explicit sharing

Morning plan 2026-04-13. Pending Ken approval before any code changes.
Emergency backup already captured at `~/Desktop/cherp emergency.zip`.

## Direction lock-in (Ken 2026-04-13)

- **Offline-first is THE anchor.** Every screen must function against
  the local device store first, sync to remote second. No screen
  should hit Supabase on the main thread of a user action.
- **Sharing system, not broadcast.** Data is owned by the individual
  who created it. They share it explicitly to specific other users.
  No more team_code broadcast channels, no more "everyone on the
  crew sees everything automatically".
- `team_codes` + `crew_members` tables become legacy metadata —
  present but unused by the new screens. No drops.
- Friend code + QR system from the sibling plan (`.claude/plans/
  friend-code-qr-rollout.md`) becomes the default way to establish a
  share relationship between two users.

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
