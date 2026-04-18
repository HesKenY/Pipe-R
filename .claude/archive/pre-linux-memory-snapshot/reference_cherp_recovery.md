---
name: CHERP offline/SW recovery escape hatches
description: Three independent paths to recover a CHERP device when a bad service-worker deploy breaks the app
type: reference
originSessionId: cb816805-8640-4246-ac34-706c900260b9
---
Phase 9a/9c shipped 2026-04-13. When CHERP won't load, feels
stuck on an old version, or the service worker is otherwise
broken, any of these three paths will recover the device. They
exist because SW caches are sticky and hard to evict.

**1. URL killswitch (fastest — no reload needed beyond the SW
unregister):**

```
https://cherp.live/demo.html?sw=off
```

Unregisters every SW, purges caches, and persists the off state
in `localStorage.cherp_sw_killswitch='1'`. Red chip appears at
bottom-right: "SW OFF — TAP TO RE-ENABLE". Tapping the chip
appends `?sw=on` and reloads. Subsequent visits stay SW-free
until `?sw=on` clears the flag.

**2. Standalone recovery page (when the app won't load at all):**

```
https://cherp.live/clear-sw.html
```

Pure HTML, no app deps. Automatically runs SW unregister + cache
purge on page load. "Also wipe offline DB + killswitch" button
for the nuclear option (clears IndexedDB too — pending writes
are lost but only if there were any). Bookmarkable.

**3. In-app admin button (superuser only):**

Admin tab → overview → "⚙ Clear SW Cache" button + "🚑 Recovery
Page" link in the superuser row. Wraps `clearCacheAndReload()`
in main.js with a confirm dialog.

**Key localStorage flags touched by these paths:**
- `cherp_sw_killswitch` — '1' when killswitch is on
- `cherp_cache_v3_phase9` — '1' after the one-time cache buster
  has run for this device

**Why: CHERP can't use Chrome DevTools on field devices.** A
worker in a basement with a broken CHERP needs to recover from
the URL bar or a bookmark. The three-path design means there's
no single failure mode that locks a user out.
