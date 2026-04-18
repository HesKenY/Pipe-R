---
name: CHERP sell model — 90-day maintained handoff
description: Commercial flow. Ken sells a branded CHERP instance per customer, built fresh from current cherp.live via Nest, maintained by Ken's team for 90 days, then handed off to the customer.
type: project
originSessionId: d3f77755-c5c8-451d-ba27-03a290c0623b
---
**The ladder (top → bottom):**

1. **Piper** — the command center. Ken's working environment.
   Lives at `C:\Users\Ken\Desktop\Claude`. Repo = HesKenY/CHERP-Backup
   (primary, since 2026-04-12 force-repoint) + HesKenY/Pipe-R (secondary).
   Runs agent_mode (Ollama training/dispatch), logging, Claude Code
   sessions, Google Sheets sync, and orchestrates everything else.

2. **Nest** (Bird's Nest) — the customer instance builder.
   Lives at `workspace/CHERP-Nest`. Repo = HesKenY/CHERP-Nest (private).
   On every build, fetches the current `HesKenY/CHERP` main via
   shallow git clone + reset, applies per-customer branding, modules,
   Supabase config, and admin account, then zips it up. The exact
   CHERP commit SHA + commit message + date is stamped into every
   customer's `instance.json` and README, so every shipped instance
   is traceable back to the cherp.live revision it was baked from.
   (Wired by Nest commit `54f1398`.)

3. **CHERP** — the product. Public repo HesKenY/CHERP, deployed to
   cherp.live via Netlify. This is what Nest bakes customer copies
   of. Its main branch IS the upstream source of truth for every
   customer build.

**The sell flow:**

- Prospect pays (terms TBD — pricing v1.1 in Desktop docs).
- Ken fires Nest for that customer (company name, colors, Supabase
  config, admin account, module selection).
- Nest fetches fresh CHERP main, bakes the branded instance, outputs
  a deployable zip + customer README.
- Instance gets deployed (Netlify or customer hosting).
- **Ken's team maintains that instance for 90 days** — bug fixes,
  schema migrations, support, feature touch-ups as CHERP main
  evolves. The exact SHA stamped in `instance.json` is the baseline.
- **After 90 days, handoff.** Customer takes ownership (runs it
  themselves OR a separate ongoing maintenance contract starts).

**Why this matters for architecture decisions:**

- Every CHERP fix Ken ships to `main` becomes a potential hot-fix
  candidate for every in-maintenance customer instance.
- Nest must keep pulling fresh on every build — stale CHERP copies
  ship yesterday's bugs to new customers.
- Supabase-per-customer isolation is a hard requirement: one
  customer's data can never touch another. Bird's Nest hub routing
  (planned, not yet built) is how the app finds the right instance.
- The trailing 90-day maintenance window is why we need strong
  logging (app_logs), traceability (instance.json source SHA), and
  a fast migration pipeline (the `migrations/` folder pattern from
  tonight's CHERP schema-drift fixes).
- The 90-day clock is also why customer handoffs need clean
  documentation — whatever we ship during that window has to be
  understandable to someone else taking over.

**How to apply:**

- When evaluating a CHERP architectural change, ask: does this help
  us maintain 10 customer instances in parallel or make it harder?
- When proposing a Piper feature, ask: does this improve our
  ability to dispatch fixes across multiple Nest-built customer
  instances, or is it just Ken-local convenience?
- When reviewing Nest changes, preserve the "fresh fetch, stamp the
  SHA" invariant. Do not let Nest bake from stale cache unless
  explicitly offline.
- When writing customer READMEs via Nest, include enough for a
  non-Ken operator to run the thing after handoff: admin creds,
  Supabase URL, module list, support contact, the exact CHERP SHA
  the instance was built from.
