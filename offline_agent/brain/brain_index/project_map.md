# Project Map — Ken's universe

This is the map of every real thing Ken is building. When the
agent asks "what project does this task belong to?" the answer
is in here. When a task crosses project lines, the answer is
*still* in here.

## Tier 1 — live products Ken is running today

### CHERP
- **What:** construction crew management platform for small
  contractors. PIN login, offline-first IndexedDB cache, GPS
  clock-in, JSA/MRO/timecards/daily-logs/messages
- **URL:** https://cherp.live (prod) + demo.html
- **Repo:** private `HesKenY/CHERP`
- **Stack:** vanilla JS + HTML, Supabase (Postgres) backend
  `nptmzihtujgkmqougkzd`, Netlify static hosting
- **Status:** LIVE. Paying is N/A — Ken runs it for friend
  businesses. Phase 2 ownership migration applied 2026-04-13.
  All screens route through `window.store` (IndexedDB +
  write-through queue). Phase 7+ queued.
- **Critical files:** `js/store.js` (read-through cache),
  `demo.html` (main entry), `cherp-schema.sql`
- **Golden rule:** never touch main without running
  `node test/run-all.js` locally and checking that cherp.live
  still loads in private window

### Pipe-R
- **What:** Node.js orchestration command center. Button-driven
  terminal UI + HTTP API + agent dispatch. Runs Ken's local
  AI squad via Ollama
- **URL:** local only (127.0.0.1:7777)
- **Repo:** private `HesKenY/CHERP-Backup` (origin) +
  `HesKenY/Pipe-R` (pipe-r remote). Both.
- **Stack:** Node.js built-ins only (no npm), Ollama models,
  Google Sheets sync via OAuth
- **Status:** daily-driver. halo-trainer + offline_agent sit
  next to it
- **Critical files:** `hub.js`, `server.js`, `agent_mode/*`

### Bird's Nest (CHERP-Nest)
- **What:** superuser/instance manager for CHERP. Builds
  custom CHERP instances for new customers
- **URL:** local only (127.0.0.1:8080)
- **Repo:** private `HesKenY/CHERP-Nest`
- **Status:** in-progress. The wizard flow needs Google Cloud
  integration (per-instance sheets + Drive + OAuth) + a
  Node dependency install hook

### Clean Money Corporation (CMC / ACE)
- **What:** S-corp co-run with Sean. Sells ACE which is a
  CHERP rebrand for specific customers
- **Site:** cleanmoneycorporation.com
- **Repo:** `HesKenY/CMC`

## Tier 2 — tooling + infra Ken owns

### halo-trainer
- **What:** scored drill environment for training Ken's agent
  squad (Ken AI, cherp-piper, qwen, forgeagent, llama3.1,
  jefferyjefferferson, m3w). Rubric-graded per drill
- **Path:** `../../halo-trainer/` (sibling of offline_agent
  in the same Codex clone)
- **Status:** operational. 5/6 drills passing on first real
  pass (2026-04-14). Ken AI v2 fine-tune corpus builds here

### offline_agent (this project)
- **What:** Ken's personal offline coding assistant. Local
  Ollama, 4-mode permissions, kill switch, brain index
- **Path:** `C:/Users/Ken/Desktop/Codex/offline_agent/`
- **Port:** 127.0.0.1:7778
- **Status:** skeleton shipped 2026-04-14. Brain rebuilt to
  the `brain_index/` + `sessions/` + `tasks/` layout

### agent_mode (in Pipe-R)
- **What:** 6-agent squad framework inside Pipe-R. Orchestrator,
  executor, registry, training log, stats engine, learning,
  dreams, per-agent memories
- **Path:** `C:/Users/Ken/Desktop/Codex/agent_mode/`
- **Status:** daily-driver. Feeds training-log.jsonl which
  seeds the Ken AI fine-tune dataset

### CodeForge
- **What:** Ken's codebase forge tool
- **URL:** codesforge.netlify.app
- **Repo:** `HesKenY/CodeForge`
- **Status:** deployed, low activity

## Tier 3 — the Halo learning rig

Not a product. An experiment. Ken plays Halo 2 MCC, the
agent squad learns. Three cooperating systems:

1. **agent_mode/halo/ (in Pipe-R)** — live loop. Keylog,
   aimbot, HUD OCR, observe/drive modes, post-mortems,
   auto-tuner, LLM patcher. This is the battlefield.
2. **halo-trainer/ (sibling project)** — classroom. Scored
   drills, rubric grading, corpus curation. This is the
   classroom.
3. **offline_agent/ (this project)** — the student. Eventually
   consumes the corpus as a fine-tune. Uses the brain index
   during normal operation

Ken plays → keylog captures → agents observe → halo-trainer
drills score them → passing rows → Ken AI v2 fine-tune.

## Tier 4 — future / not yet built

- **Google Cloud for Nest wizard** — per-instance Google Sheets
  + Drive + OAuth provisioning during CHERP instance build
- **Ken AI v2 real fine-tune** — once training-log.jsonl has
  ~200 clean rows from halo-trainer corpus, run actual fine-tune
- **CHERP web integration with Sheets** — add `sheet_url`
  column to `team_codes`, show "view in sheets" button on
  cherp.live
- **Pipe-R web UI** (`pipe-r.html`, `remote.html`) — the deck
  is partially built, remote.html referenced by server.js
- **Phase 4.5 Nest backend adapter** — swap CHERP's `store.js`
  to write through a `NEST()` backend instead of Supabase for
  pilot customers (JSBackyard, REVV)

## What this agent should NEVER touch
- cherp.live `main` branch without Ken's explicit go-ahead
- production Supabase schemas (use migrations, never ad-hoc
  ALTER)
- pushed git history (no force push, no history rewrite)
- any .env or credentials.json or token.json files
- Ken's personal Gmail, Calendar, billing, or Supabase auth
