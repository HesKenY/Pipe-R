---
name: Crew Management Redesign Plan
description: Plan for rebuilding crew management — current system has lookup bugs, needs cleaner flow for superusers and workers.
type: project
originSessionId: c25daccd-a89c-4ade-896e-c5ad4a5ab41b
---
## Current Problems
- Team code lookup fails despite API returning correct data — likely browser/cache/SW issue
- Superusers see "join crew" prompt but shouldn't need to join — they manage all crews
- The flow mixes registration-time crew joining with post-login crew joining
- No visual crew browser for superusers

## Redesign Plan
1. **Superuser view:** Skip "join crew" — show a crew dashboard with all crews, members, and tasks
2. **Foreman view:** Show their crew + ability to create new crews
3. **Worker view:** Show join prompt with code entry OR browse available crews
4. **Crew creation:** Foreman/superintendent creates crew → gets code → shares with workers
5. **Crew assignment:** Superintendent can assign workers to crews without the worker needing a code

## Test Build Needed
- Create a standalone test page (crew-test.html) that just tests Supabase team_codes queries
- Isolate the lookup issue from the app's service worker / caching layers

**How to apply:** The current crew system works at the API level but breaks in the browser. Fix the browser issue first, then redesign the UX flow.
