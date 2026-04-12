# Session Log

Date: 2026-04-10

## What Was Done
- Google Sheets Sync: auth.js, schema.js, sync.js — full push/pull engine, zero deps
- Hub.js [G] menu, server.js 4 endpoints + 15-min auto-sync timer
- Google OAuth authorized (project cherp-493003, account kdeibel.pipedown@gmail.com)
- Alpha Crew spreadsheet created and synced live
- CLAUDE.md updated with Sheets docs + Future section
- Pipe-R pushed to GitHub (43fea8f, 34d38c7)
- Created user account: thall / 1234 / journeyman / ALPHA-01
- Icon modernization across all CHERP screens (9 files, 6 icon swaps)
- CHERP pushed to GitHub

## Tomorrow — Priority Order
1. **Ken AI** — personality coding model, frame using agent_mode training pipeline
2. **Website version with local storage** — personal Google integration, offline-capable
3. **Android multi-instance architecture** — Hub routing, Play Store onboarding
4. **CHERP web Sheets button** — finish sheet_url column + mycrew.js button
5. **Nest wizard Google Cloud steps** — auto-provision Sheets per instance

## Architecture Notes for Tomorrow

### Website Version — Local Storage + Personal Google
Ken wants a version of CHERP that runs with local storage (browser-side) and personal Google account integration. The idea: a lightweight personal version where your data lives in YOUR Google Sheets/Drive, not in a company Supabase instance. Could serve as:
- Personal work diary / timecard tracker
- Individual tool that syncs to company instance when connected
- Standalone mode for independent contractors
Think: PWA with localStorage + Google Sheets as the "database"

### Android Multi-Instance Network
When a company buys CHERP, Nest provisions their own Supabase instance. Workers download ONE universal app from Play Store, enter a team code, and get routed to the correct company instance.

**Central Hub** (one Supabase project):
- `instance_registry` table: team_code → supabase_url, anon_key, company_name
- Read-only for the app, zero user data stored
- Only cross-instance connection point

**Flow:** Download app → enter team code → Hub lookup → connect to company instance → create account there

**Security:** Instances never talk to each other. Hub only maps codes to URLs. RLS handles everything within instances.

**Open questions:**
- Hub = existing project or new dedicated one?
- One code per crew or one per company?
- Cache instance URL permanently or re-check?
- Worker switching companies?
- Google Sheets provisioning per-instance via Nest?

### Nest Wizard — Google Cloud Integration
When Nest builds a new CHERP instance, it should also:
- Create Google Spreadsheet set for that company
- Set up OAuth credentials for Sheets sync
- Store sheet URLs in instance's team_codes
- Register team codes in the Hub routing table
