---
name: CHERP Design Principles
description: Core design rules for building CHERP — offline-first, GPS trust, role-based access, Pipe-R as journeyman.
type: feedback
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
- **Offline-first matters more than real-time sync** on construction sites. Workers are in basements, tunnels, rural sites. The app must work without internet and sync when connected.
- **Instant page sync on workers' clients is a priority** (added 2026-04-12). When a foreman creates a task, assigns an MRO, or files a JSA, the workers on that crew should see it on their home/tasks/mycrew screens **immediately** without having to manually reload. Extend the existing Supabase Realtime subscription in `js/main.js startRealtime()` — currently only covers `pipe_messages` — to also cover `crew_tasks`, `crew_timecards`, `crew_mros`, `crew_jsa`, and `crew_incidents` filtered by the active `team_code`. On a matching `INSERT`/`UPDATE`, re-render whichever screen is currently visible.
- **Manual sync button** (added 2026-04-12). Realtime over WebSocket is fragile on construction sites (sketchy cell, service worker weirdness, bad wifi). Always expose a sync button — on the top bar or inside each screen — that lets the worker/foreman force a reload of the current screen against the live Supabase instance. This is the "I know it's stale, refresh NOW" lever when Realtime didn't fire.
- **GPS + selfie verification for time clocks is a trust mechanism, not surveillance.** It proves the worker was on site — protects them as much as the company. Frame it that way in the UI.
- **Role-based access is critical.** An apprentice sees different things than a superintendent. Don't show admin features to field workers. Don't hide field tools from admins.
- **The AI assistant (Pipe-R) should feel like a knowledgeable journeyman, not a chatbot.** It knows codes, specs, field math. It talks like someone who's carried the pipe. Not corporate, not academic.

**Why:** These are Ken's foundational design decisions. They come from real field experience and shape every UI and feature decision.

**How to apply:** Every new feature, screen, or interaction should be evaluated against these four principles. If something doesn't work offline, it's not ready. If it exposes admin data to workers, it's wrong. If Pipe-R sounds like a help desk, rewrite it.
