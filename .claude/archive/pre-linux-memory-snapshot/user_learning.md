---
name: Ken's Learning Tracker — Apprenticeship Program
description: Tracks Ken's growing technical knowledge so Claude can ramp up language and complexity over time.
type: user
originSessionId: 612ace6e-1cd4-4973-a8c2-48e2d51c1a07
---
## Current Level: Beginner → Intermediate
Ken builds through AI tools, not by writing code directly. Understands project structure, file roles, and what things do at a high level. Now designing multi-system architectures and directing cross-platform integrations.

## Concepts Understood
- Git basics (commits, push, pull, branches, remotes)
- Repo structure (files, folders, what goes where)
- Netlify deploys (push triggers build, build logs, publish directory)
- PWA basics (manifest, service worker, install prompt)
- Supabase as a backend (auth, database, API keys, REST API)
- Client vs server keys (knows service key is sensitive)
- HTML/CSS/JS file roles (markup, styling, logic)
- Project architecture (multi-file vs monolith)
- Google OAuth2 flow (credentials → consent → token → refresh)
- Google Sheets API as a data layer (tabs, sync, backup)
- Server endpoints (REST pattern, JSON responses, port binding)
- Agent/model dispatch (Ollama models with specialized roles)
- Hub.js TUI menu pattern (button-driven, wired into mainMenu)
- Google Cloud Console basics (projects, APIs, OAuth consent, test users)

## Concepts In Progress
- RLS (Row Level Security) — knows it exists, hasn't configured it
- Serverless functions — knows they're the fix for exposed keys
- Multi-instance architecture — designing Hub routing pattern for CHERP scaling
- API design / REST patterns — seeing how endpoints compose into systems
- Training data pipelines — JSONL format, prompt/response capture
- Schema vs code drift — introduced 2026-04-12 via the crew_tasks bug: `tasks.js` wrote columns that the live Supabase table never had (`work_type`, `photo_b64`, `done_at`, `progress`, `due_date`), every INSERT returned 400. Showed Ken that the code file and the actual database are two different sources of truth that can drift apart.
- DDL vs DML — introduced alongside the above: ALTER TABLE is DDL (structure changes) and needs to run in the Supabase SQL editor, while normal reads/writes are DML and go through the REST API.

## Concepts Not Yet Introduced
- Database schema design (beyond existing tables)
- Build tools / bundlers
- Testing
- TypeScript
- CI/CD pipelines
- Environment variables / secrets management (beyond basic)
- DNS / domain configuration
- Android app deployment (Play Store, signing, Capacitor)

## Session Notes
- 2026-04-09: First tracked session. Ken understands platform architecture deeply. Comfortable directing AI agents across repos. Diagnosed Codex damage and directed repair strategy.
- 2026-04-10: Built full Google Sheets sync system. Ken navigated Google Cloud Console (OAuth consent, test users, API enabling). Designed multi-instance CHERP architecture (Hub routing, instance isolation). Thinking at systems level now — "string Supabase instances together" shows architectural instinct.
- 2026-04-12: Ken used "continuity" correctly ("run through claude files for continuity") — understands that session logs + memory + CLAUDE.md are the state-recovery mechanism across sessions. Also independently noticed the crew/tasks bug from field use and prioritized fixing it before continuing Ken AI. First real exposure to schema/code drift and DDL vs DML.

## How to Apply
- Start explaining *why* things work, not just doing them silently
- Introduce one new concept per session when natural — don't force it
- Use the term first, then explain in plain language
- As concepts move from "In Progress" to "Understood", drop the parenthetical explanations
- Never talk down — Ken has deep domain knowledge in construction and business, just not in code syntax
- Ken is progressing fast — he's designing multi-tenant architectures now. Match the pace.
