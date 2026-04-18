---
name: CHERP Personal/Website Version
description: Lightweight CHERP version using localStorage + personal Google Sheets/Drive as the database, no Supabase needed
type: project
originSessionId: 612ace6e-1cd4-4973-a8c2-48e2d51c1a07
---
Ken wants a personal version of CHERP that runs with browser localStorage and personal Google account integration.

**Concept:** A lightweight PWA where your data lives in YOUR Google Sheets/Drive, not in a company Supabase instance.

**Use cases:**
- Personal work diary / timecard tracker for independent contractors
- Individual tool that syncs to company instance when connected
- Standalone offline mode — no server dependency at all
- "Old fashioned" clients who just want spreadsheets

**Architecture idea:** localStorage as primary DB, Google Sheets as backup/sync target. Could bridge into a company instance later via team code.

**Why:** Some users don't need/want a full platform. This gives them CHERP's UI with Google as the backend. Also serves as the advertised "spreadsheet-friendly" mode.

**How to apply:** This is a separate build target or mode within CHERP. Consider it when designing the multi-instance architecture — personal mode is an instance of one.
