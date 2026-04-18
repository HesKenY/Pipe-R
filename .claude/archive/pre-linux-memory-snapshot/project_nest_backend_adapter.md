---
name: Nest Backend Adapter (Phase 4.5)
description: Future CHERP direction — swap Supabase for per-company Nest backend via store.js adapter, phased not forklift
type: project
originSessionId: 3bf2fe6f-d592-495f-b593-e98003f3c998
---
**Direction**: Eventually write Supabase out of CHERP and replace it with a
per-company backend hosted inside Bird's Nest (SQLite + lightweight WebSocket
chat + file blobs on local disk). `store.js` was built first specifically to
make this a one-file client swap.

**Why the store-first ordering matters**:
Because `store.js` is the only file that talks to the backend, swapping
Supabase for a NEST() call becomes a single-file client change. Phases 1-3
prove the abstraction against a known-good remote before we introduce a
second backend.

**What we gain by writing Supabase out**:
- No CSP / connect-src headaches (already hit this class of bug)
- No service key in client JS (the known security issue in memory)
- Per-company data isolation at the process level, not RLS-policy level —
  a stronger guarantee than row-level security
- Private chat network per company for free, not as a separate product
- Zero monthly cost until scale past VPS-per-customer
- Offline-first works even against the foreman's laptop on home wifi,
  because Nest can run on that box

**What we lose**:
- Supabase Realtime QoL (reconnect backoff, presence) — rebuild lightweight
- Built-in Postgres query power — SQLite is 95% there but not identical
- Hosted dashboard for inspecting data — need a Nest admin screen (already
  being built for Bird's Nest anyway)
- Point-in-time backups — replace with nightly SQLite file copy

**Phased approach, not a forklift**:
1. Finish phases 1-3 on Supabase (prove the store abstraction against a
   known-good remote)
2. Phase 4.5 — add a `NEST()` backend as a PARALLEL option in `store.js`,
   not a replacement. Selected per-instance via config flag.
3. Pilot customers (JSBackyard, REVV) ship on Nest-backed instances from
   day one. Supabase stays as the dev/test default.
4. Eventually Supabase gets retired — after Nest adapter is battle-tested
   through pilots.

**The sweet spot**: chat networks. Supabase Realtime has limits + RLS
friction for channels. A per-company WebSocket chat is easiest to build
fresh (maybe 150 LOC inside Nest).

**Why: How to apply:**
- Why: `store.js` is the abstraction layer that makes this feasible. If
  screens talked to Supabase directly, this would be a rewrite.
- How to apply: Do NOT start the Nest adapter during phases 1-3. Keep
  `store.js` pure to one backend for now. Revisit after phase 3 ships
  and tasks.js + timeclock.js are proven on Supabase+store.js. When
  resuming, the change is a new `js/store-nest.js` or a backend flag in
  `store.js`, plus a matching endpoint surface inside Nest.
