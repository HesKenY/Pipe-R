---
name: Pilot customers — JSBackyard + REVV
description: First two test customer instances scheduled to be built via Nest. Both are friends' businesses doing real-world CHERP testing for Ken.
type: project
originSessionId: d3f77755-c5c8-451d-ba27-03a290c0623b
---
**Added 2026-04-12.** Ken has lined up two friendly pilots to test the full Nest → branded CHERP → 90-day maintenance flow before charging strangers.

1. **JSBackyard** — a friend's business, field-testing the CHERP platform. Slug TBD.
2. **REVV** — another friend's business. Reusing this name intentionally — previously "REVV" was the mistaken rename Codex did in 2026-04-08 (see `project_naming.md`), now being reclaimed as a real customer handle.

**Why it matters:**

- First two real exercises of the `/api/nest/build` endpoint shipped in Piper commit `68a6cd3`.
- First two customer records to land in `agent_mode/config/customers.json`.
- First two 90-day maintenance clocks to start ticking (per the sell model in `project_sell_model.md`).
- Friends = lower-stakes feedback loop. Use this window to find bugs in the Nest build pipeline, the branding injection, the admin-account seeding, and the customer-README output before a paying customer sees any of it.

**How to apply when building these:**

- Run the build via `/api/nest/build` (or Nest's terminal wizard) so the source CHERP commit SHA gets stamped into each instance's `instance.json`.
- Stamp the build event in `customers.json` so Piper's dashboard shows them and the 90-day expiry is tracked.
- Keep a short notes field per pilot covering: what they're testing, what broke, what they want changed, what they loved.
- Don't over-customize — brand colors + company name + admin account is enough for pilots. Save deep customization for paying customers.
- Expect to ship hotfixes to cherp.live mid-pilot, which means the 90-day maintenance window includes pushing fresh builds (via Nest, not direct file edits) when real bugs are found.
