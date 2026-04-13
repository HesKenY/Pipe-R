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

## Resolved decisions — Ken 2026-04-13 answers

Captured here as load-bearing architecture. Every bullet below is
**approved and must be honored** through every phase. Any plan item
that contradicts one of these must be rewritten.

### Ownership (section A resolved)

- **A1 Workers own their own tasks, foremen see progress via
  downstream visibility** (reports_to chain). Individual task system
  ships FIRST and must be test-green. Foreman-downstream view is a
  second visit on top.
- **A2 Multi-assignee = task copy per assignee.** When a foreman
  "assigns" one task to three workers, the system clones the task
  into three independently-owned rows. Each assignee owns their
  copy. Edits are independent thereafter — if Worker B's copy
  evolves, Worker A's copy is unchanged. The foreman sees the whole
  cohort via downstream visibility.
- **A3 Placeholder names for unregistered workers.** Foreman types
  "Mike" in the assignee field. If no matching user_profile exists,
  CHERP creates a `task_placeholder` row (or an internal
  `pending_user` stub) with the typed name. The task's assignment
  points at the placeholder. When "Mike" signs up and his
  display_name matches, the signup flow prompts "There are N
  pending tasks assigned to you — claim them?" → links the
  placeholder to his new user_profiles.id. Formal signup completes
  the loop.
- **A4 MRO stays request-based for now.** Not inventory tracking.
  An MRO row is "I need X delivered to the site tomorrow." No
  company-asset ownership. Park the virtual "Company" user idea.
- **A5 Historical orphans** — null owner_id, admin claim UI.

### Hierarchy + reports_to (section B resolved)

- **B1 Recursive depth cap = 5** ✓
- **B2 Vacated foreman = ghosted placeholder.** When a foreman
  leaves (or is deactivated), their row gets a `status:
  'placeholder'` flag, their user card is greyed out and marked
  "unavailable". The `reports_to` rows pointing at them stay intact
  so the chain doesn't break. A push notification fires to the
  next level of supervision ("GF needed: replace foreman X on crew
  Y") with a deep link to the reassignment screen. Crew + workers
  stay visible + functional while the seat is vacant.
- **B3 Crews are hot-swappable at the worker level.** A worker can
  request to leave crew A and join crew B. Request fires a
  notification to the receiving foreman with an approval link.
  Approve = move the worker, update reports_to, notify the original
  foreman. Reject = nothing changes.
- **B4 Demotion gets the same clean path.** Foreman demoted →
  their reports_to rows walk up one level automatically (to their
  own supervisor), and a notification fires to the new supervisor
  listing the incoming direct reports. If the demotion target
  disagrees with the reassignment, they use the normal reassign
  flow to redistribute.
- **B5 Ghosted snapshot** — placeholder user rows preserve the
  display_name, role title, crew association, but show as greyed-
  out with a "seat vacant — awaiting assignment" badge. No login
  possible against a ghosted row.
- **B6 Prevent circular references via chronological order.**
  Since `reports_to` is set at hire time and only changes via
  explicit reassignment, the system can enforce: "when setting
  reports_to = X, walk X's chain upward; if the walk ever returns
  to the subject, reject." Plus a 5-level depth cap for safety.
- **B7 Drill-down supervisor navigation.** GF's Manage tab shows
  their direct reports (foremen). Tapping a foreman drills into
  THAT foreman's workers. Another tap drills into the worker's
  tasks/timecards. Not one flat query — layered navigation with
  breadcrumbs.

### Conflicts + offline (section C resolved)

- **C1 Save both edits, never silently drop.** Every edit is
  timestamped + signed with the account that made it. Notes are
  append-merged. For scalar-field clashes (description, priority,
  status) on the same record, the LOSING edit is preserved in an
  `edit_conflicts` table and a notification fires to the next
  higher supervisor in the chain to make the call: "Worker A
  changed the task description to X, Worker B changed it to Y.
  Which one stands?" The chosen version applies; the rejected
  version is kept in audit for reference. **Merge information,
  never delete.**
- **C2 Task notes append-merge** — JSON array sorted by timestamp,
  both edits survive.
- **C3 Timecard approval flow — full spec:**
  - **Workers can only clock in/out themselves** — no external
    punch-in capability.
  - **Foremen can EDIT existing timecards** owned by their
    downstream, but cannot CREATE new punches for them.
  - **Superintendents can add / remove / edit** any timecard in
    their chain.
  - **Workers request changes** to their own timecards (e.g. "I
    forgot to clock out at 4pm, please fix to 4:30pm"). Request
    pushes up to the next editable level in the chain (foreman,
    then superintendent). On approve, the edit applies immediately.
  - **Daily sync + weekly sync cadence** — timecards batch-submit
    once per day AND once per week.
  - **Worker approves their own full week report** before it
    flows to payroll. The week summary shows every punch, any
    edits made by foreman/super, and a big "Approve for payroll"
    button. Payroll only sees approved weeks.
- **C4 Per-install device UUID** on every edit for conflict
  attribution.
- **C5 CACHE_VERSION bump on store schema changes.**
- **C6 IndexedDB retention policy + photo offload to Supabase
  Storage on sync.**

### New architecture pieces these answers introduce

Three new cross-cutting systems have to land alongside the store:

1. **Notifications + approval chain table**
   ```sql
   CREATE TABLE notifications (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     recipient_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
     kind TEXT NOT NULL CHECK (kind IN (
       'crew_swap_request','crew_swap_approved','crew_swap_rejected',
       'foreman_vacant','demotion_reassignment','timecard_edit_request',
       'timecard_edit_approved','timecard_edit_rejected',
       'conflict_resolution_needed','task_shared','placeholder_claim'
     )),
     title TEXT NOT NULL,
     body TEXT,
     action_link TEXT,      -- hash route the recipient taps into
     related_item_type TEXT,
     related_item_id TEXT,
     read_at TIMESTAMPTZ,
     responded_at TIMESTAMPTZ,
     created_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```

2. **Placeholder users table**
   ```sql
   CREATE TABLE pending_users (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     display_name TEXT NOT NULL,
     created_by UUID REFERENCES user_profiles(id),
     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
     claimed_by_user_id UUID REFERENCES user_profiles(id),  -- set on claim
     claimed_at TIMESTAMPTZ
   );
   ```
   Assignee fields on tasks become `assigned_to_user_id UUID` (real
   user) OR `assigned_to_pending_id UUID` (placeholder). On signup,
   CHERP scans `pending_users` for name matches and offers to claim.

3. **Edit conflict escalation table**
   ```sql
   CREATE TABLE edit_conflicts (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     item_type TEXT NOT NULL,
     item_id TEXT NOT NULL,
     field_name TEXT NOT NULL,
     edit_a_value TEXT,
     edit_a_by UUID REFERENCES user_profiles(id),
     edit_a_at TIMESTAMPTZ NOT NULL,
     edit_b_value TEXT,
     edit_b_by UUID REFERENCES user_profiles(id),
     edit_b_at TIMESTAMPTZ NOT NULL,
     resolver_id UUID REFERENCES user_profiles(id),
     resolved_value TEXT,
     resolved_at TIMESTAMPTZ,
     status TEXT NOT NULL DEFAULT 'pending'
       CHECK (status IN ('pending','resolved','both_kept'))
   );
   ```

These three tables go into the phase 2 migration alongside owner_id.

---

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

## Simulated conflict tests

Walking each scenario end-to-end with the approved rules above to
verify the system actually handles it seamlessly. Format per test:
actors → timeline → expected outcome → verification step.

### SIM-1 Two-device same-user clock-in

**Actors**: Worker Mike has CHERP on his phone AND his tablet. Both
are offline (no cell, job site basement).

**Timeline**:
- 08:00 Mike clocks in on the phone. Local store writes a
  `crew_timecards` row with `device_id=phone-uuid`, `user_id=mike`,
  `clock_in=08:00`. Queued for sync.
- 08:02 Mike notices the tablet open, taps "Clock in" on it. Local
  store on the tablet doesn't know about the phone's row yet. Writes
  a SECOND row with `device_id=tablet-uuid`, same user, `clock_in=08:02`.
- 09:00 Mike steps outside, phone reconnects first, syncs the 08:00
  row → server.
- 09:01 Tablet reconnects, tries to sync the 08:02 row. Server already
  has an active open-shift row for Mike.

**Desired outcome**: the tablet's sync detects an existing open shift,
merges the two rows into one (earliest clock_in wins = 08:00), keeps
the losing edit in `edit_conflicts`, notifies Mike "you clocked in on
two devices — we kept the 08:00 punch from your phone." No duplicate
timecard, no lost punch, no payroll confusion.

**Fix baked into store**: every timecard write checks for an open
shift for the same user_id before inserting. If one exists, the newer
attempt becomes a note on the existing row instead of a new row.

**Seamless**: ✅ — Mike never sees a duplicate, the system picks the
first-clock-in-wins, both attempts are audit-logged.

---

### SIM-2 Concurrent edit of the same task description

**Actors**: Foreman A and Foreman B both edit Worker X's task
"Demo old cabinets" offline (X reports to both via multi-crew).

**Timeline**:
- 13:00 Foreman A edits the task description to "Demo old cabinets,
  save the pantry doors", offline. Stored with edit_a_at=13:00,
  device_id=A's phone.
- 13:02 Foreman B edits the same task description to "Demo old
  cabinets, keep the soffit above", offline. Stored with edit_b_at=13:02,
  device_id=B's phone.
- 13:30 Both foremen reconnect within a minute of each other.
- Foreman A syncs first. Server accepts, task description becomes A's
  version.
- Foreman B syncs. Store detects the remote `updated_at > local.synced_at`
  AND the field `description` changed AND B's local edit differs from
  both the pre-edit state and the new remote state.

**Desired outcome per C1**: don't silently clobber. Create an
`edit_conflicts` row (both versions preserved), fire a notification to
the next higher supervisor in the chain (probably the superintendent
who oversees both foremen) with a deep link to the resolve screen. Both
A and B see a yellow "conflict pending" badge on the task. The
superintendent taps the notification, sees both versions side-by-side,
picks one (or types a third), and applies.

**Fix baked into store**: on sync, if local edit conflicts with remote
edit on the same field, write to `edit_conflicts` instead of overwriting.
Both values survive.

**Seamless**: ⚠️ PARTIAL — seamless for data preservation (nothing lost),
NOT seamless for user experience (both foremen see a pending-conflict
badge until resolved). Accept that trade — C1 explicitly wants "merge
information rather than delete."

---

### SIM-3 Notes append-merge

**Actors**: Worker M and Foreman F both add notes to the same task
offline.

**Timeline**:
- 10:00 Worker M adds note "Ran into hidden plumbing behind the wall,
  called the plumber" offline. Local notes array: [{text: "Ran into...",
  by: M, at: 10:00, device_id: m-phone}].
- 10:15 Foreman F adds note "Approved overtime for this job" offline.
  Local notes array: [{text: "Approved overtime...", by: F, at: 10:15,
  device_id: f-phone}].
- 10:30 Both sync. Store merges the notes arrays by sorting on `at`.

**Desired outcome**: final notes array has BOTH entries in chronological
order, each with byline + device. No conflict, no escalation, no data
loss.

**Fix**: store's sync resolver treats JSON-array fields as append-merge
by default.

**Seamless**: ✅ — no user intervention needed, both notes visible
immediately.

---

### SIM-4 Share revocation race

**Actors**: Foreman F reassigns task T from Worker A to Worker B while
A is editing it offline.

**Timeline**:
- 11:00 Task T is assigned to Worker A (implicit share:
  owner=F, shared_with=A, can_edit=true).
- 11:05 A goes offline, starts editing the task progress to 50%.
- 11:10 F, online, reassigns T to Worker B. Server:
  - Revokes A's share (sets revoked_at).
  - Creates new share for B.
  - Updates `assigned_to_user_id` to B.
- 11:30 A comes back online, tries to sync their local progress=50%
  edit. Server checks: A no longer has an active share on this task.

**Desired outcome**: A's edit gets preserved in the `edit_conflicts`
table (they made a legitimate edit before the revocation reached them),
a notification fires to F saying "Worker A updated task T after
reassignment — here's what they changed: progress=50%. Apply it or
discard?" F can choose to apply A's edit to the now-B-owned task or
discard it. A's app shows a toast: "Task T was reassigned while you
were offline. Your progress update was passed to the foreman."

**Fix baked into store**: the sync engine checks share state BEFORE
writing. If the writer's share is revoked, route the edit to an
escalation path instead of failing.

**Seamless**: ✅ — A's work isn't lost, F has the final call, no silent
drop.

---

### SIM-5 Hierarchy reorg during timecard edit

**Actors**: GF reassigns Worker X from Foreman A → Foreman B.
Foreman A is mid-edit of X's timecard offline.

**Timeline**:
- 07:00 X reports to A (A is X's upstream foreman).
- 07:30 A, offline, opens X's timecard and edits clock_out to 16:30.
- 08:00 GF, online, updates X's reports_to = B. Server writes the change.
- 08:15 A comes online. Tries to sync the timecard edit. Store checks:
  does A still have edit access to X's timecard? Via downstream
  visibility, NO — A is no longer X's foreman.

**Desired outcome per B2+C3**: A's edit is preserved in `edit_conflicts`
+ a notification fires to B (the NEW foreman) saying "Former foreman A
edited X's timecard at 07:30 (clock_out=16:30). Apply or discard?" B
has immediate edit rights now and can decide. A sees a toast: "X was
transferred to a different crew during your edit. Your timecard change
was handed off to their new foreman for review."

**Fix**: sync engine checks the writer's current permission (via
reports_to chain + crew membership, at sync time, not at edit time).
Permission-less edits escalate instead of failing.

**Seamless**: ✅ — A's data survives, B gets the hand-off with context,
no manual coordination needed between the two foremen.

---

### SIM-6 Delete-vs-edit race

**Actors**: Foreman F deletes task T offline. Worker M edits task T
offline during the same window.

**Timeline**:
- 09:00 F marks task T for deletion offline. Local: `deleted: true`.
- 09:10 M adds a note and marks progress=75% offline. M doesn't know
  the task was marked deleted because they're also offline.
- 09:30 F syncs first. Server soft-deletes T (sets deleted_at).
- 09:45 M syncs. Store checks: task T is soft-deleted. M's edit can't
  just overwrite.

**Desired outcome**: M's note + progress are preserved in a "zombie"
audit entry linked to the deleted task. A notification fires to F:
"Worker M updated task T after you deleted it — note + progress=75%.
Undelete to keep their work, or discard?" F decides.

**Fix baked into store**: use soft-delete (deleted_at timestamp)
instead of hard delete. Edits arriving after a soft-delete escalate to
the deleter via notification.

**Seamless**: ✅ — M's work preserved, F has the final call.

---

### SIM-7 Employee ID collision on simultaneous signup

**Actors**: Two users hit the CHERP signup form within the same
second. Both get display_name starting with "KD".

**Timeline**:
- 10:00:000 User 1 submits signup. Client generates `KD-04829`.
- 10:00:001 User 2 submits signup. Client also generates `KD-04829`
  (unlikely with a 100k suffix space but possible).
- 10:00:050 User 1's row inserts, `employee_id=KD-04829` claimed.
- 10:00:051 User 2's row tries to insert, UNIQUE constraint fails with
  23505.

**Desired outcome**: User 2's signup retries with a new random suffix
automatically (client-side, transparent). Retry up to 5 times. If all
5 collide, escalate to random letters (not initials) for the 6th try.
User 2 never sees an error unless all 6 fail in a row (~probability
zero at 100k space).

**Fix baked into signup**: catch 23505 on INSERT, regenerate code,
retry. No user-facing error message unless 6 retries exhaust.

**Seamless**: ✅ — neither user knows there was a collision.

---

### SIM-8 Stale service worker cache

**Actors**: Worker on their phone. Didn't open CHERP for a week. In
that week, phase 5 shipped and added a new `owner_id` column to
`worker_certifications`.

**Timeline**:
- Day 0 Worker last used CHERP. SW cached app shell v3.1.
- Day 7 Phase 5 ships. Service worker in the deployment is v3.2 with
  the new store schema.
- Day 7 Worker opens CHERP. SW activation check: worker's local
  CACHE_VERSION=3.1, deployed version=3.2. Mismatch.

**Desired outcome**: SW detects the version mismatch, forces a full
reload of the app shell + IndexedDB schema upgrade + hard-reload to
pick up new code. Worker sees a brief "Updating CHERP..." splash, then
the new app. Their local unsynced edits (if any) survive the upgrade
via a dedicated `pending_sync` object store that the schema upgrade
preserves across migrations.

**Fix baked into service worker**: every deploy bumps CACHE_VERSION.
On activation, SW clears old caches + triggers IndexedDB schema
upgrade via `onupgradeneeded`. Migration logic maps old schema to new
schema, preserving `pending_sync` unchanged.

**Seamless**: ✅ — one-second splash screen, everything preserved.

---

### SIM-9 Timecard approval flow end-to-end

**Actors**: Worker W submits timecards for the week. Foreman F approves
edits. Superintendent S processes payroll.

**Timeline**:
- Mon 07:00 W clocks in. Local row, syncs on reconnect.
- Mon 16:00 W clocks out. Syncs.
- Tue-Fri W repeats. All punches owned by W, visible to F via downstream
  visibility.
- Fri 16:30 W notices Tue's clock-out was wrong (forgot to punch). W
  opens the timecard for Tue, taps "Request edit" → types "Forgot to
  clock out, should be 16:30" → submits. Store writes a `notifications`
  row with `kind=timecard_edit_request`, `recipient=F`.
- Fri 16:35 F gets the notification, taps through. Sees W's Tuesday
  punch, the requested edit, the original time, and two buttons:
  "Approve" / "Reject". F taps approve. Store updates the timecard
  row with the edited clock_out, writes an audit note signed by F
  ("edited per W's request at 16:35 Fri"), writes a `notifications`
  row back to W ("Your Tuesday timecard was approved").
- Sat 09:00 W opens the week report. Sees every punch for the week,
  F's approval note, and a big "Approve week for payroll" button. W
  reviews everything, taps approve. The week's timecards get marked
  `worker_approved_at = now()`, locking further worker edits.
- Mon S runs payroll. Query: all `crew_timecards` where
  `worker_approved_at IS NOT NULL AND week = <last_week>`. Those flow
  to payroll. Unapproved timecards don't.

**Desired outcome**: W approves their own week, S processes only
approved weeks, F sees + approves edits. Daily sync (every 24h) + weekly
sync (Sunday night batch to ensure everything is in the store before
Monday payroll run).

**Fix baked into schema**:
- `crew_timecards.worker_approved_at TIMESTAMPTZ` column
- `crew_timecards.edited_by UUID REFERENCES user_profiles(id)`
- `crew_timecards.edit_reason TEXT`
- Notifications table for the request → approve flow

**Seamless**: ✅ — every actor has a clear step, nothing breaks offline,
payroll never sees unapproved data.

---

### SIM-10 Orphan items after user delete

**Actors**: Superintendent deletes Worker X's account. X had 40 tasks,
12 timecards, and 3 certifications in the system.

**Timeline**:
- Day 0 X's row gets soft-deleted (sets `user_profiles.is_active=false`
  and `deactivated_at=now`). Actual row stays to preserve FK integrity.
- Day 0 All items owned by X have a dangling owner_id from a feed
  perspective — they still exist, but no active user to feed them to.
- Day 1 F (X's former foreman) opens the Manage tab. Downstream query
  returns X's items because FOR 30 DAYS after deactivation, the
  chain walk includes deactivated users with `deactivated_at >
  now() - 30 days`.
- Day 31 X's items drop out of F's default view. They're still in the
  DB, still visible via an "Archived" admin filter.

**Desired outcome**: a 30-day grace window where deactivated users'
work is still in their foreman's feed so anything in progress can be
wrapped up. After 30 days, items archive (soft-hidden) but never
delete. Admin can always surface them.

**Fix baked into visibility query**: the downstream walk explicitly
includes `is_active=true OR deactivated_at > now() - interval '30 days'`.

**Seamless**: ✅ — transitions are grace-gated, nothing snaps out of
view immediately.

---

### SIM-11 Photo blob sync lag

**Actors**: Worker W attaches a 4 MB photo to a task offline.

**Timeline**:
- 11:00 W takes a photo, attaches to task T. Local store writes the
  task row with `photo_b64=<4MB base64>` AND queues a
  `pending_photo_upload` job with the blob.
- 11:05 W back online. Store sync fires.
- 11:06 Task row sync: store PATCHes the remote with the task fields
  but NOT the b64 photo (too big for PostgREST). Instead, it POSTs
  the blob to Supabase Storage at
  `photos/<task_id>/<uuid>.jpg`, gets back a URL, then PATCHes the
  task row with `photo_url=<url>` and clears the local b64.
- 11:07 Foreman F opens the task on their device, sees the photo via
  `<img src=photo_url>`.

**Failure case**: upload fails (network flaky, Storage quota hit).
Store keeps the blob local, the task row shows "photo pending upload"
until the next sync attempt. Every 60s the sync engine retries
`pending_photo_upload` jobs. After 10 failures it surfaces a banner
"Photo upload stuck — tap to retry or dismiss."

**Fix baked into store**: photos are a separate queue from task data.
Task metadata syncs fast, photos sync whenever they can. UI shows a
small "📷 uploading" badge on tasks with pending photos.

**Seamless**: ✅ — task data never blocked by photo upload, photo
eventually lands, worst case shows a retry prompt.

---

### SIM-12 IndexedDB corruption mid-write

**Actors**: W's phone crashes mid-write (OS kill, battery died).

**Timeline**:
- 12:00 W taps "Clock out" while offline. Store opens an IndexedDB
  transaction to write a timecard row + a pending_sync entry + a
  notification ("clocked out 12:00").
- 12:00:050 Phone dies with the transaction half-complete. IDB rolls
  back the transaction atomically.
- 12:30 W boots phone, opens CHERP. The clock-out did NOT persist.
  W sees the punch screen still showing "CLOCKED IN since 08:00".
  W taps clock-out again. Works.

**Desired outcome**: IndexedDB's atomic transactions mean we NEVER see
half-writes. W just has to retry. If the store detects a "clocked in
>12 hours" state on app open, it flags "did you forget to clock out?"
as a nudge.

**Fix**: store only writes via IDB transactions that encompass BOTH
the data row AND the sync queue entry. Atomic or nothing.

**Seamless**: ⚠️ PARTIAL — user has to retry, but nothing is corrupted
and nothing is silently dropped. Accept.

---

### Summary — what the sims proved

| # | Scenario | Seamless? | Mechanism |
|---|---|---|---|
| 1 | Two-device clock-in | ✅ | First-wins + merge-on-write |
| 2 | Concurrent description edit | ⚠️ Partial | Preserve both + escalate |
| 3 | Notes append-merge | ✅ | Array merge by timestamp |
| 4 | Share revocation during edit | ✅ | Escalate to current owner |
| 5 | Hierarchy reorg during edit | ✅ | Escalate to new supervisor |
| 6 | Delete vs edit race | ✅ | Soft-delete + zombie escalation |
| 7 | Employee ID collision | ✅ | Retry loop, invisible |
| 8 | Stale SW cache | ✅ | Version bump + forced upgrade |
| 9 | Timecard weekly approval | ✅ | Explicit approve button |
| 10 | Orphan items after delete | ✅ | 30-day grace + archive |
| 11 | Photo blob sync lag | ✅ | Separate queue + retry |
| 12 | IDB corruption mid-write | ⚠️ Partial | Atomic tx, user retries |

**12 of 12** scenarios have a clear resolution. **10 of 12** are fully
seamless (user never sees friction). **2 of 12** (scalar-edit conflict
+ mid-write crash) require at most one user action to resolve.

No scenario silently drops data. Every conflict is either auto-resolved
or escalated up the chain with a notification. Every edit is attributed
to a device_id + user_id + timestamp for audit.

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
| **4.5** | **Nest backend adapter (stub)** — add a `NEST()` backend to `store.js` as a parallel option alongside Supabase, selected per-instance via config flag. Pilot customers ship on Nest-backed instances from day one. Supabase stays dev/test default. See `memory/project_nest_backend_adapter.md` for the full rationale. | Medium — new backend, but `store.js` was built first specifically so this is a one-file swap | Flip config flag back to SB |
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
