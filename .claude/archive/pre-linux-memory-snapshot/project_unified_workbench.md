---
name: Unified workbench — Piper + Nest + Claude + Agent Mode
description: Piper, Nest, Claude Code, and agent mode all run together inside C:\Users\Ken\Desktop\Claude. Launching Piper co-launches Nest. Ken drives via Piper windows, Claude directs via sessions, agent mode is shared runtime.
type: project
originSessionId: d3f77755-c5c8-451d-ba27-03a290c0623b
---
**The mental model Ken stated 2026-04-12:**

> "Agent mode is intended to work in Nest for build with Claude. I will use these terminals as my controller, the windows are meant for buttons and click-through menus but you will direct the agents here, I will direct them through Piper."

Translation — there are two directors pointing at the same agent runtime, with two different UIs:

| who | how they direct agents | where they see results |
|---|---|---|
| Ken | clicks buttons in Piper (pipe-r.html web UI, or hub.js terminal) | same Piper UI, plus the trainer deck party cards |
| Claude (me) | `/api/dispatch` from Claude Code sessions | terminal output + training-log.jsonl back-stamps |

Both paths hit the **same** merged orchestrator in `agent_mode/core/` with the same party (5c1z0r / R0t0m / D3c1du3y3 / P0ryg0n / Umbr30n / 4l4k4z4m + Ken AI trainer + M3w Promptdex companion). Every dispatch — regardless of originator — gets logged to `training-log.jsonl` with a `taskId` for review/back-stamp.

**Physical layout — everything inside `C:\Users\Ken\Desktop\Claude`:**

```
C:\Users\Ken\Desktop\Claude\
├── PIPE-R.bat         ← double-click: launches everything
├── START.bat          ← quick stop+start+hub (terminal)
├── STOP.bat           ← quick kill :7777
├── NEST.bat           ← launches Nest alone
├── server.js          ← Piper HTTP API on :7777
├── hub.js             ← Piper terminal TUI
├── pipe-r.html        ← Trainer Deck web UI (served by server.js)
├── remote.html        ← phone remote web UI
├── agent_mode/        ← the shared agent runtime
│   ├── core/          ← orchestrator, queue, registry, executor
│   ├── config/        ← agents.json, runtime.json, tasks.json
│   ├── ken/           ← Ken AI profile + Modelfile
│   ├── training/      ← training-log.jsonl + charters + curate.js
│   └── sheets/        ← Google Sheets sync
└── workspace/         ← gitignored, holds sub-repos
    ├── CHERP/         ← HesKenY/CHERP clone (cherp.live source)
    └── CHERP-Nest/    ← HesKenY/CHERP-Nest clone (builder)
```

**Launcher behavior (2026-04-12):**

- **PIPE-R.bat** — starts server.js on :7777 if not running, co-launches Nest in its own terminal window, opens pipe-r.html in browser. Three windows come up: Piper server, Bird's Nest, Trainer Deck.
- **NEST.bat** — launches Nest alone in current window (for when you just want to bake a zip).
- **START.bat / STOP.bat** — quick Piper server/hub control (terminal-first fallback).

**Git / backup layout:**

- **Piper** → `HesKenY/CHERP-Backup` (primary, origin) + `HesKenY/Pipe-R` (secondary). Private. Both receive every commit.
- **Nest** → `HesKenY/CHERP-Nest`. Private. Nest repo's own origin.
- **CHERP** → `HesKenY/CHERP`. Public. The upstream source Nest bakes customer zips from.

Nest's `instance-builder.js` is the load-bearing piece: every customer build shallow-clones HesKenY/CHERP main, stamps the exact commit SHA into the instance manifest, then brands+bakes. So every shipped customer instance is traceable to a specific CHERP revision.

**The Piper → Nest bridge:**

The goal state (being built incrementally 2026-04-12 late session):
1. `/api/nest/build` in server.js — POST takes customer config, imports Nest's InstanceBuilder, runs the build, records the result in `agent_mode/config/customers.json`
2. `/api/nest/customers` in server.js — GET returns the registry with days-remaining in the 90-day maintenance window
3. `agent_mode/config/customers.json` — { id, slug, name, status, buildSha, buildAt, expiresAt, modules, notes }
4. Eventually: "Build Customer" button in pipe-r.html that calls /api/nest/build
5. Eventually: agent mode hooks into Nest's build steps (Umbr30n runs QA on the baked zip, D3c1du3y3 audits branding, P0ryg0n summarizes the build log)

**How to apply:**

- When adding any new Piper feature, ask: does it need to be reachable from both Claude and Ken's Piper UI? If yes, expose it as an HTTP endpoint so both can hit it.
- When adding any Nest feature, ask: will Piper need to trigger this programmatically? If yes, make it importable from server.js, not just CLI-interactive.
- Never break the "same orchestrator instance for both directors" rule. There is one agent_mode/core/orchestrator.js. It's shared.
- Launcher changes: PIPE-R.bat is the canonical double-click. Anything that makes PIPE-R.bat heavier needs a reason. Anything that splits it into multiple launchers needs a better reason.
- Git hygiene: every session should end with both Piper remotes up-to-date. Nest remote up-to-date. CHERP main up-to-date. The four-repo sweep is the end-of-session ritual.
