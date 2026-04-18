---
name: CHERP Security — Service Key Exposure
description: Supabase service role key is in client-side JS (config.js). Needs to move behind serverless functions eventually.
type: project
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
The Supabase service role key (`SB_SVC`) is currently exposed in `js/config.js` in the public CHERP repo. It's used by:
- `js/auth.js` — account creation/upsert
- `js/utils.js` — API helper headers
- `js/screens/admin-panel.js` — all admin operations

This key bypasses Supabase RLS (Row Level Security), meaning anyone who reads the source can make admin-level API calls.

**Why it's there now:** The app needs it to function. Stripping it broke crew management, manage, and admin screens.

**How to apply:** Don't strip the key again without a replacement (serverless functions or edge functions to proxy admin calls). Ken wants to address security incrementally as he learns — don't push a big security refactor unprompted. Flag issues, explain tradeoffs, implement when Ken's ready.
