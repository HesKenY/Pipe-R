# Friend Code + QR Rollout Plan — CHERP

Phased migration from the current shared-`team_code` onboarding model
to a per-user friend code + QR scan flow. Must be **seamless**: every
existing crew + user keeps working unchanged, every phase ships
independently without breaking anything, and the old team_code path
stays as a fallback until it's explicitly retired.

Owner: Ken + Claude. Drafted 2026-04-13.

---

## 0. Why this change

Current model:
- Foreman creates a crew → gets a 6-char `team_code` like `WS5A3Q`
- Shares that code with every crew member (SMS, verbally, whatever)
- Anyone who knows the code can join that crew

Problems:
1. **Leaks**: codes get screenshotted, photographed, overheard. Once a
   code is out, anyone can join the crew.
2. **Not portable**: moving a worker between crews means re-sharing a
   new code.
3. **Feels unprofessional**: it's a shared Wi-Fi password, not a real
   account system.
4. **Doesn't scale**: large GCs with subcontractors bouncing between
   crews need per-worker identity, not per-crew.

Target model (Xbox Live / PSN / Discord style):
- Every user has a stable personal friend code like `KD-4829`.
- Foreman adds a worker by typing or scanning their friend code.
- Worker gets a pending invite notification, accepts or rejects.
- `crew_members` row is created on accept. User's `team_code` gets set
  to the inviting crew.
- Workers can be on multiple crews over time without re-issuing codes.

---

## 1. Schema additions

One migration. **Additive only** — nothing dropped, nothing renamed,
nothing breaks existing rows.

### `user_profiles.friend_code`

```sql
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS friend_code TEXT;

-- Generate friend codes for every existing row that doesn't have one.
-- Format: 2 uppercase letters + "-" + 4 digits. 676 * 10000 = 6.76M
-- distinct codes, plenty of headroom.
UPDATE user_profiles
SET friend_code = concat(
  chr(65 + floor(random() * 26)::int),
  chr(65 + floor(random() * 26)::int),
  '-',
  lpad(floor(random() * 10000)::text, 4, '0')
)
WHERE friend_code IS NULL;

-- Now make it mandatory + unique. UNIQUE is the collision protection.
ALTER TABLE user_profiles
  ADD CONSTRAINT user_profiles_friend_code_unique UNIQUE (friend_code);
ALTER TABLE user_profiles
  ALTER COLUMN friend_code SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_profiles_friend_code
  ON user_profiles (friend_code);
```

On collision during backfill (unlikely at Ken's scale but possible),
the UNIQUE constraint fails and the migration can be rerun — it'll
skip the rows that already have a code and only re-generate the
duplicates.

### `crew_invites` — new table

```sql
CREATE TABLE IF NOT EXISTS crew_invites (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  team_code       TEXT NOT NULL REFERENCES team_codes(code) ON DELETE CASCADE,
  from_user_id    UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  to_friend_code  TEXT NOT NULL,
  to_user_id      UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
  role            TEXT NOT NULL DEFAULT 'journeyman',
  status          TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending','accepted','rejected','expired','cancelled')),
  message         TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  responded_at    TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days')
);

CREATE INDEX IF NOT EXISTS idx_crew_invites_to_friend_code
  ON crew_invites (to_friend_code) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_crew_invites_team_code
  ON crew_invites (team_code);
```

RLS policy: only the `from_user_id` foreman or the `to_user_id` recipient
can SELECT. Only the recipient can PATCH (to accept/reject). Only a
foreman can INSERT. Superuser bypasses via service key.

### Friend code format helper

```javascript
// js/utils.js — used by both signup and invite display
function generateFriendCode(displayName) {
  // Prefer initials from the display name, fall back to random letters.
  const letters = displayName
    ? displayName
        .split(/\s+/)
        .map(w => w[0])
        .filter(c => c && /[A-Za-z]/.test(c))
        .slice(0, 2)
        .map(c => c.toUpperCase())
        .join('')
    : '';
  const prefix = letters.length === 2
    ? letters
    : String.fromCharCode(65 + (Math.random() * 26) | 0)
      + String.fromCharCode(65 + (Math.random() * 26) | 0);
  const digits = String((Math.random() * 10000) | 0).padStart(4, '0');
  return `${prefix}-${digits}`;
}
```

"Ken Deibel" → `KD-0000` to `KD-9999`. Only 10k codes per initials pair
but the retry-on-collision loop handles it. Pre-collision attempts:
try with initials → if taken after 3 retries, fall back to random
letters.

---

## 2. UI surface — where this shows up

### A. Profile screen (every user)

Display the user's friend code prominently + a QR code rendered
client-side. No dependency on Supabase.

```
┌────────────────────────────────┐
│  Ken Deibel                    │
│  Foreman · CHERP               │
│                                │
│  ╔══════════════════╗          │
│  ║  ██▄▄ ▄▄  ██▄▄  ║          │
│  ║  ▄█▀▀ ▀▀  █▀▀▀  ║          │
│  ║  (QR code)      ║          │
│  ╚══════════════════╝          │
│                                │
│  Friend code: KD-4829          │
│  [Copy] [Share]                │
└────────────────────────────────┘
```

QR payload format: plain `KD-4829` string. No URL scheme, no token —
adding a user still requires foreman auth + crew context, so a leaked
QR can't do harm.

QR renderer: ship a tiny inline generator (~3 KB gzipped). No npm,
no CDN fetch. Candidate: `qrcode.min.js` from davidshimjs/qrcodejs —
vanilla JS, MIT licensed, drops in as a single file.

### B. Crew management — "Add by Friend Code"

In `crews.js renderManageWorkers()`, add a button row at the top:

```
┌─ Add Worker ───────────────────┐
│ Friend code: [     _ _-_ _ _ _]│
│              [Add] [Scan QR]   │
└────────────────────────────────┘
```

- **Add** — POST a `crew_invites` row with `from_user_id = _s.id`,
  `to_friend_code = <input>`, `team_code = _s.teamCode`, status =
  `pending`.
- **Scan QR** — opens the camera, reads the code, prefills the input,
  then runs the same Add path. See Section 4 for the scanner.

After POST, show a toast: "Invite sent to KD-4829 — waiting for accept".

### C. Home screen badge — pending invites for me

Every worker's home screen polls `crew_invites?to_friend_code=eq.<mine>&status=eq.pending`
every 30s and shows a badge if any are pending.

Tap → modal:

```
┌─ Crew Invites ─────────────────┐
│ J. Heath wants to add you to   │
│ Test Crew as Journeyman        │
│                                │
│ [Accept]  [Decline]            │
└────────────────────────────────┘
```

Accept handler:
1. PATCH `crew_invites` → status=accepted, responded_at=now,
   to_user_id=_s.id
2. PATCH `user_profiles` → team_code=<invite.team_code>
3. POST `crew_members` → member_name, role from invite, device_id
4. Toast: "Joined Test Crew ✓"

Decline handler: PATCH status=rejected, responded_at=now. That's it.

### D. Legacy join-by-code fallback

Keep the old "Join crew by code" flow exactly as it is today. Nothing
breaks for crews that haven't migrated yet. Eventually move it behind
an "Advanced" or "Legacy" disclosure, but don't remove it.

---

## 3. Signup flow change

Current (`auth.js registerNewUser()`):
- User enters name, PIN, role, optional team code → row inserted

New:
- Same inputs
- Generate friend_code via the helper above
- Retry up to 5 times on UNIQUE collision (fallback to random letters
  after 3 retries)
- Insert row with friend_code set
- Show the new friend code on the post-signup screen: "Your friend code
  is KD-4829. Share it with your foreman so they can add you to a crew."

No functional change to PIN login or any existing screen. The team_code
entry field stays optional and still works.

---

## 4. QR scanner implementation

Two paths depending on platform support:

### 4a. Chrome Android (primary)

Use the built-in `BarcodeDetector` Web API:

```javascript
if ('BarcodeDetector' in window) {
  const detector = new BarcodeDetector({ formats: ['qr_code'] });
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment' }
  });
  // draw stream to a <video>, then periodically:
  const codes = await detector.detect(videoEl);
  if (codes.length) {
    stopStream();
    input.value = codes[0].rawValue;
    // → triggers the existing Add handler
  }
}
```

Chrome Android has `BarcodeDetector` since ~2022. Zero bundle cost.

### 4b. iOS Safari + older Chrome (fallback)

`BarcodeDetector` isn't available. Options:
1. **Manual entry only** — scanner button hidden on unsupported browsers,
   user types the 6 chars. Ship this in Phase 4.
2. **jsQR** — 45 KB minified, drop-in QR decoder that runs on a canvas
   frame. Ship in Phase 5 if field users actually need it.

Start with 4a + manual fallback. Measure who's on iOS before adding the
bundle cost of jsQR.

### 4c. Android wrapper app

The `CHERP-Android` WebView needs camera permission added to the
manifest + a JavaScript bridge or just rely on the browser's
`getUserMedia` (works inside WebView if the activity has
`CAMERA` permission).

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" android:required="false" />
```

MainActivity needs `onPermissionRequest` on the WebChromeClient to grant
the camera permission to the WebView when `getUserMedia` is called.
One method override, ~10 lines.

---

## 5. Phased rollout — each phase is independently shippable

| Phase | Ship | Breaks anything? |
|---|---|---|
| 1. Schema migration | `friend_code` column, `crew_invites` table | No — additive only |
| 2. Signup writes friend_code | `auth.js registerNewUser()` patch | No — old rows already backfilled |
| 3. Profile screen shows friend_code + QR | `employee-card.js` + tiny QR lib | No — read-only display |
| 4. "Add by friend code" button (text entry) | `crews.js` new input + POST invite | No — parallel path, team_code fallback stays |
| 5. Pending invites badge + accept flow | `home.js` poll + modal + handlers | No — only affects users with pending invites |
| 6. QR scanner (Android primary) | `BarcodeDetector` integration | No — just fills the existing input |
| 7. Deprecate shared team_code sharing UI | Hide "Share crew code" button behind Admin | No — API still works |
| 8. iOS fallback (optional) | jsQR bundle | No — only loaded on iOS |

Ship phases 1-6 to CHERP `dev` branch → field-test → merge to `main` →
Netlify deploys. Each phase is a single-commit PR.

Phases 7 + 8 happen after field-test feedback.

---

## 6. Data migration for existing crews

No data needs to move. The rollout is purely additive:
- Existing `user_profiles` rows get a backfilled `friend_code` in
  Phase 1
- Existing `crew_members` rows are untouched
- Existing `team_codes` rows are untouched
- A foreman who wants to migrate their crew to friend-code invites can
  do so organically: each new worker joins via invite, old workers
  stay via their existing `team_code` until they drop off

No "migration day". No flag day. No downtime.

---

## 7. Android wrapper changes (CHERP-Android)

Already built as a WebView wrapper that points at
`https://cherp.live/demo.html`. Every phase above ships to Netlify
and is instantly available in the wrapper on next reload.

One native change needed for Phase 6 (QR scanner):
- Add `<uses-permission android:name="android.permission.CAMERA" />` to
  `AndroidManifest.xml`
- Override `WebChromeClient.onPermissionRequest()` in `MainActivity.kt`
  to grant `PERMISSION_VIDEO_CAPTURE` to the WebView
- Bump `versionCode` + rebuild APK

Optional Phase 6b: add a **Share Friend Code** intent filter so tapping
a `cherp://add/KD-4829` URL from another Android app opens CHERP with
the code prefilled. Nice-to-have.

---

## 8. Testing plan

### Per-phase tests

- **Phase 1 (schema)**: apply to a Supabase branch preview, verify
  every `user_profiles` row has a unique `friend_code`, verify no row
  has duplicates.
- **Phase 2 (signup)**: create 20 new test users in rapid succession,
  verify all 20 get unique codes, verify the collision-retry loop
  fires at least once (use a deterministic seed).
- **Phase 3 (profile QR)**: manually scan each test user's QR with a
  second phone, verify the decoded string matches `friend_code`.
- **Phase 4 (add by code)**: as a foreman, add a test user by typing
  their code. Verify the `crew_invites` row lands. Verify RLS blocks
  non-foreman POST.
- **Phase 5 (accept flow)**: as the recipient, accept the invite.
  Verify `user_profiles.team_code` updates, `crew_members` row lands,
  badge clears. Reject path: verify no crew_members row, badge clears.
- **Phase 6 (scanner)**: scan a code with Chrome Android + the CHERP
  WebView app. Verify camera permission prompt fires exactly once.
- **Cross-phase**: full round trip — new user signs up, foreman adds
  by code (not QR), user accepts, verify they appear in the crew list.

### Live Test Mode integration

Extend the `kitchen-remodel-3day` scenario to cover the invite path:
1. Create 3 user_profiles (get auto-generated friend codes)
2. Foreman POSTs `crew_invites` for each of the 2 workers
3. Workers PATCH the invites to `accepted`
4. Verify `crew_members` rows appear with the correct `member_name`
   and `role`

Team B's QA agent (Umbr30n) should fail the round if any invite
doesn't round-trip cleanly.

### Field test checklist (when ready to promote to main)

- [ ] Migration applied to Supabase prod, no constraint violations
- [ ] All existing users have friend_code populated
- [ ] Ken's own profile shows the correct QR + code
- [ ] Ken can create a new user from the admin panel and immediately
  see their friend code
- [ ] Ken can add a test worker to `WS5A3Q` via friend code + the worker's
  phone receives the invite within 30s
- [ ] Worker accepts, shows up in the crew list
- [ ] No regression on the legacy team_code join path

---

## 9. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Collision during signup explodes 500 | UNIQUE constraint → retry loop with random fallback after 3 tries |
| Existing apprentices get confused by 2 join flows | Keep old flow in place, only surface new flow where relevant |
| Invite spam by a malicious foreman | Rate limit: max 50 invites per foreman per day |
| Stale invites cluttering the table | `expires_at` 7 days, plus a nightly cron to mark expired |
| QR privacy | Friend code alone is inert — adding requires foreman auth + crew context, so scraping is harmless |
| iOS can't scan | Manual entry works, add jsQR in Phase 8 if field feedback demands |
| Database migration hits RLS during backfill | Run the UPDATE as superuser / service key, not as an authenticated user |
| Worker on multiple crews creates `crew_members` duplicates | Unique constraint on `(team_code, user_id)` — if missing, add in Phase 1 migration |

---

## 10. Open questions — decide before Phase 1

1. **Initials-based or random friend codes?** Recommended: initials
   with random fallback. Friendlier for verbal sharing, still unique.
2. **Does `team_code` ever get removed from `user_profiles`?** No —
   keeps Pipe-R's Live Test scenarios working + the legacy join path.
3. **Multiple pending invites to the same user?** Allowed. User sees a
   list and accepts one at a time. Accepting one doesn't cancel
   others.
4. **Superuser-only friend code generation or self-service?**
   Self-service at signup. No gatekeeping.
5. **Change friend code after signup?** Not in v1. Frozen at signup.
   Add a "rotate code" admin action in v2 if a code ever leaks in a
   way that matters.
6. **Invite lifetime?** 7 days default. Foreman can re-send.

---

## 11. What Pipe-R needs to do about this

- **Live Test scenarios** — add a variant `kitchen-remodel-3day-invites`
  that uses the invite path end-to-end. Ship alongside Phase 5.
- **CHERP CLAUDE.md** — document `crew_invites` table + the invite
  flow so future Claude sessions don't accidentally bypass it.
- **Patch plan template** — when a Live Test round fails an invite
  acceptance, surface it as a high-severity issue in the next patch
  plan.
- **Android wrapper** — Phase 6 native permission change (camera),
  versionCode bump, rebuild and reinstall APK on the phone.

---

## 12. Estimated effort

- Phase 1 (schema): 1 hour — write + apply migration
- Phase 2 (signup): 1 hour — auth.js change + test
- Phase 3 (profile QR): 2 hours — QR lib integration + profile UI
- Phase 4 (add by code): 2 hours — crews.js input + invite POST
- Phase 5 (accept flow): 3 hours — home.js poll + modal + handlers
- Phase 6 (QR scanner): 3 hours — BarcodeDetector + camera permission
  + Android manifest change + testing on real device
- Phase 7 (deprecate legacy): 30 min — move button
- Phase 8 (iOS fallback, optional): 2 hours — jsQR bundle

**Total: ~14 hours of build + test time.** Not a single session —
spread across 3-4 sessions of focused work, with a field test between
Phase 5 and Phase 6.

---

## 13. Go/no-go checklist for Ken

Decide these before I touch any code:

- [ ] Format: `KD-4829` style OK?
- [ ] Keep team_code fallback permanently, or plan to retire?
- [ ] 7-day invite expiry OK?
- [ ] Phase order OK or do you want to ship Phase 3 (QR display) before
      Phase 4 (add by code) so workers see their codes first?
- [ ] Field test between Phase 5 and Phase 6 — or try to ship all six
      in one go?
- [ ] Should the Android wrapper get the camera permission change NOW
      (so it's in place when Phase 6 ships) or defer until Phase 6?

Answer any or all, then I start with the Phase 1 migration.
