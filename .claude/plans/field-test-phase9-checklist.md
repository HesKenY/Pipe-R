# CHERP field-test checklist — Phase 9 offline-first

Generated 2026-04-13 after merging Phase 9a+9b+9c. Before running
this, make sure `b05f2bf` or later is live on cherp.live (Netlify
takes ~30s after each push to `main`).

## 0. Pre-flight (once, before going to site)

- [ ] Open cherp.live on **two separate devices** — Ken's phone +
  Sean's phone, ideally. Hard-refresh each twice (first load runs
  the one-time cache buster, second load installs the new SW).
- [ ] **DevTools → Application → Service Workers** on at least
  one device: verify `cherp-v3.0.0-phase9` shows as "activated".
- [ ] **Application → Cache Storage**: should show one entry
  (`cherp-v3.0.0-phase9`) with 28 files inside.
- [ ] Log in as a real test user (not superuser).
- [ ] **Application → IndexedDB → cherp_store**: after 1-2 seconds
  post-login, the `rows` object store should have entries for
  `crew_tasks`, `crew_mros`, `pipe_messages`, `crew_timecards` if
  there's any data on that team. This proves the warmer fired.
- [ ] Bookmark `cherp.live/clear-sw.html` on both devices.

## 1. Offline baseline — the core claim

This is what has to work, period.

- [ ] Log in. Poke around — open Tasks, Chat, Work (MROs), Safety,
  Timeclock, Library. Let every screen render at least once.
- [ ] Enable **airplane mode**. Wait 2 seconds.
- [ ] The amber offline bar should appear at the top.
- [ ] **Reload the page**. The app shell must still load — don't
  close the tab, just hit refresh. If the app boots to a blank
  page here, that's a hard fail; tap `/clear-sw.html` and redeploy.
- [ ] Navigate between tabs. Every tab should render from cache.
- [ ] Open a task. Check its comment thread (💬 button, Phase 7b).
  Existing comments should load from IDB. Try to add a new one —
  it should appear instantly, and the offline bar should flip to
  show "OFFLINE — 1 change queued".
- [ ] Clock in. Toggle a task. Edit an MRO note. Every write
  should succeed from the user's point of view, and the queued-
  count in the offline bar should increment.
- [ ] Turn airplane mode **off**. Within ~5 seconds the offline
  bar should transition from red (OFFLINE) → amber (SYNCING — N
  pending) → gone.
- [ ] Hard refresh. Every queued write should now appear in
  Supabase — verify by opening admin panel on the other device
  and confirming the rows landed.

## 2. Cold-start offline — the harder scenario

Does the app work after being completely dead, loading into a
network with no Supabase reachable?

- [ ] Log out.
- [ ] Fully kill the browser tab.
- [ ] Enable airplane mode.
- [ ] Re-open cherp.live. App shell must load. (Login will fail
  against Supabase, but the shell should render.)
- [ ] Try a hardcoded fallback login (Ken's dev PIN). It should
  still authenticate — js/config.js has hardcoded fallbacks.
- [ ] Home screen should render. Any previously-warmed data for
  that user (from the last session's warmer) should still be
  visible — tasks, MROs, chat history.
- [ ] Turn airplane mode off → live data should start flowing.

## 3. Pending-sync counter UX

- [ ] With offline bar visible ("OFFLINE — N change(s) queued"),
  the N count should accurately reflect `store.pendingCount()`.
  It should not get stuck.
- [ ] When online and actively syncing, the bar should briefly
  turn amber with "SYNCING — N pending" before disappearing.
- [ ] If there are no pending writes, the bar stays hidden when
  online.

## 4. Service worker update path

- [ ] Ken pushes a small change to main → Netlify redeploys.
- [ ] Within 5 min (the interval is hardcoded in main.js) the
  update banner should appear at the top of the screen.
- [ ] Tap the banner → app should reload **exactly once** and
  the new SW should be active. Verify via DevTools → Application.
- [ ] No infinite reload loop. If you see one, the killswitch is
  your escape hatch.

## 5. Killswitch — the escape hatches (CRITICAL)

Everyone on the field test needs to know these. If anything goes
sideways tomorrow, these are the recovery paths:

**Quickest (URL-only):**
```
https://cherp.live/demo.html?sw=off
```
Unregisters the SW, purges caches, persists the off state. Red
"SW OFF — TAP TO RE-ENABLE" chip appears at bottom-right. The
app will work, just without offline support, until you tap the
chip or visit `?sw=on`.

**Full recovery page:**
```
https://cherp.live/clear-sw.html
```
Standalone HTML, has no dependencies, unregisters SWs + purges
caches automatically on load. "Also wipe offline DB + killswitch"
button for the nuclear option (clears IDB too — pending writes
are lost).

**In-app (superuser):**
Admin tab → "⚙ Clear SW Cache" button in the superuser-only row.
Same as the recovery page but keeps the user logged in.

## 6. What to watch for that I haven't tested

- **iOS Safari**: service workers in a PWA installed via "Add to
  Home Screen" behave differently from Safari tab contexts. If a
  field tester is on iOS, check both modes — installed PWA AND
  Safari tab.
- **Android WebView wrapper**: CHERP-Android points at cherp.live
  via Tailscale IP. The wrapper has its own cache independent
  of the system Chrome, so `?sw=off` applied in Chrome does NOT
  affect the wrapper. To clear the wrapper's SW, open its URL
  inside the wrapper and hit `?sw=off` there.
- **Multi-tab**: if two CHERP tabs are open on the same device,
  IndexedDB can get into a lock state during a schema upgrade.
  Phase 9 doesn't bump DB_VERSION but keep one tab at a time to
  avoid weirdness.
- **Back-to-back offline edits**: the local-id → server-id swap
  on create + sync is well-tested in isolation, but not against
  a real scenario of "clock in offline, add a note offline,
  delete the note offline, come back online" in one streak.
  If any of those silently fail, the audit log + admin panel
  will tell us.
- **pipe_messages growth**: the warmer pulls the full message
  history for a team on every login. On a team with thousands
  of messages this is slow. Not a tomorrow problem but note it.

## 7. Reporting back

Log bugs as you find them, ideally in the Pipe-R worklist or a
quick Discord/text to Ken. For each, note:

- Device (make + OS + browser/app)
- Reproduction steps
- Whether `/clear-sw.html` or `?sw=off` recovers the device
- Screenshot or screen recording if you can grab one

Happy field test.
