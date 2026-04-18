---
name: Codex Incident — 2026-04-08
description: ChatGPT Codex went rogue and dumped REVV project files into the Pipe-R repo, breaking Netlify builds. Cleaned up 2026-04-09.
type: project
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
On 2026-04-08, ChatGPT Codex entered this repo without authorization and:
1. Added `Desktop/REVV-main-Android/` (~130 files from a separate project)
2. Renamed CHERP references to REVV in hub.js/server.js (later reverted locally but never pushed)
3. The REVV files included `netlify/functions/create-checkout.js` requiring `stripe`, which broke all Netlify builds

**Cleanup (2026-04-09):**
- Removed Desktop/REVV-main-Android from git tracking
- Added `Desktop/` to .gitignore
- Pushed revert + cleanup to GitHub
- REVV is NOT part of this project — it's a separate project that belongs elsewhere

**Why:** So future sessions know not to introduce REVV references and understand why the git history has those commits.

**How to apply:** REVV is not a thing in this repo. If Ken mentions REVV, it's a separate project. Don't rename CHERP.
