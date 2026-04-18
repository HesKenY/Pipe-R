---
name: Google Sheets Sync Reference
description: OAuth credentials, sheet IDs, and sync config for CHERP Google Sheets backup system
type: reference
originSessionId: 612ace6e-1cd4-4973-a8c2-48e2d51c1a07
---
**Google Cloud project:** cherp-493003
**OAuth client ID:** 294359454385-u6n51uhkub2d5dkm75e0406gl7dhtaf2.apps.googleusercontent.com
**Auth email:** kdeibel.pipedown@gmail.com (added as test user in OAuth consent screen)
**Token location:** agent_mode/sheets/token.json (gitignored)
**Credentials JSON:** agent_mode/sheets/credentials.json (copied from Desktop)

**Alpha Crew sheet:** https://docs.google.com/spreadsheets/d/1QwE0Aur8BVd0SrAee6OnXA7QKY9-1F0NJBo0v8mwnNY
**Supabase key for sync:** Provided at runtime via SUPABASE_SERVICE_KEY env var (project nptmzihtujgkmqougkzd)

**Auto-sync:** server.js pushes every 15 minutes when token exists and crews configured.
**Status:** OAuth authorized 2026-04-10. App still in "testing" mode in Google Cloud — needs publishing for production use.
