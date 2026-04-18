---
name: CHERP Multi-Instance Network Architecture
description: Android app routes workers to correct company Supabase instance via central Hub lookup using team codes
type: project
originSessionId: 612ace6e-1cd4-4973-a8c2-48e2d51c1a07
---
Ken's vision for scaling CHERP to multiple companies. Each company gets its own Supabase instance (provisioned by Nest wizard). Workers download one universal Android app from Play Store.

**The Bridge pattern:**
- Central "Hub" Supabase holds ONLY a routing table: `team_code → instance_url, anon_key, company_name`
- Worker enters team code → app queries Hub → gets company instance URL → connects directly
- App caches instance URL locally after first lookup
- Hub is read-only, stores zero user data — only connection point between instances
- Company instances are fully isolated from each other

**Security model:** Only cross-instance data is team_code → URL mapping. No credentials, no user data in Hub. RLS handles everything within instances.

**Open questions (2026-04-10):**
- Hub = existing nptmzihtujgkmqougkzd or new dedicated project?
- One team code per crew or one master code per company?
- App cache permanently or re-check Hub?
- Worker switching companies flow?
- Google Sheets provisioning per-instance via Nest wizard?

**Why:** Ken wants to sell CHERP as instances to construction companies. Workers need a simple onboarding: download app, enter code, land in correct company. No cross-contamination between company data.

**How to apply:** This shapes Nest wizard, Android app architecture, and Supabase project strategy going forward.
