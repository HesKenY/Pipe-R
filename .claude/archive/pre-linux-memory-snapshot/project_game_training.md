---
name: Game-based AI training — Pokemon + Factorio
description: AI training environments Ken is using to train Ken AI; Halo stack stays but active work is on turn-based games
type: project
originSessionId: 4f2069d0-f62b-4932-beb3-48c801257e56
---
Ken is training his AI agents against video games as a grounded learning
environment. As of 2026-04-16, the direction pivoted from Halo MCC
(real-time FPS) toward turn-based / strategy games — **Pokemon Crystal**
(via mGBA) and **Factorio** are the two candidates he's leaning toward.

**Why:** Pokemon (and Factorio) mirror the mental model of *running
CHERP* — turn-based decisions, party/crew management, task routing,
inventory, objectives. Halo is reflex-driven and doesn't transfer; a
party-management game does. Training Ken AI to play Pokemon well is
practice for the real job (running CHERP operations).

**How to apply:**
- The Halo stack (`agent_mode/halo/`, halo-memory.md, keylog, aimbot,
  trainer, post-mortem, dreams) stays in place. Don't delete it — it's
  paused, not retired.
- Active game-training work lives at `Codex/agent_mode/pokemon/` and
  `Codex/agent_mode/factorio/` — both already scaffolded with kenai:v1
  wired in via vision + screen capture (NOT the Claude folder).
- Corpora live at `Codex/corpora/<game>/` and feed `Codex/offline_agent/
  brain/training/` as JSONL alongside Modelfile iterations.
- DO NOT scaffold parallel game folders in `C:\Users\Ken\Desktop\Claude`.
  That folder is stale relative to Codex; check Codex first.
- When proposing agent training work, default to Pokemon / Factorio
  scenarios over Halo ones. Halo is only touched on explicit request.
- The "pokemon ≈ running CHERP" framing matters: party management,
  turn-based reasoning, and objective tracking are the transferable
  skills. Keep agent features grounded in that analogy.

**v0 scaffold shipped 2026-04-16:** `pokecrystal/bridge.lua` (mGBA TCP
server), `pokecrystal/agent.py` (Python brain loop), `ram_map.json`,
seeded `poke-memory.md`. Emulator = mGBA.
