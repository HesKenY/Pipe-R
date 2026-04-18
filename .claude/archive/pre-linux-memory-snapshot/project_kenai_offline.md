---
name: Ken AI = kenai:v1 offline Claude Code (Codex workspace)
description: Ken AI is a real Ollama model (kenai:v1) being built as an offline Claude Code. Active workspace is Codex folder, NOT Claude folder.
type: project
originSessionId: 4f2069d0-f62b-4932-beb3-48c801257e56
---
**CRITICAL ORIENTATION (corrected 2026-04-16):** Ken's "Ken AI" is not
the qwen2.5-coder:14b-with-Modelfile pattern in the Pipe-R repo. It's
a real Ollama model `kenai:v1` being iterated as an **offline Claude
Code** — a fully local coding assistant that mimics what Claude Code
does but runs on Ken's hardware with no cloud dependency.

**Active workspace:** `C:\Users\Ken\Desktop\Codex\` (NOT `Claude\`).
The Claude folder has stale, parallel work. Codex is canonical.

**Key Codex paths:**
- `Codex/offline_agent/` — the offline Claude Code being built. Has its
  own `brain/`, `frontend/`, `models/`, `agent_core/`, `halo_tools/`.
- `Codex/offline_agent/brain/training/modelfiles/` — 20+ timestamped
  iterations of `kenai-v1.Modelfile` and `kenaiofflinev0v1.Modelfile`,
  plus `*.unsloth.jsonl` training datasets.
- `Codex/brain/` — TOP-LEVEL BRAIN repo (different from offline_agent's
  brain). Multi-repo indexing/dataset system. Only ingests repos in
  `Codex/brain/repositories.json`. Read `BRAIN_CHARTER.md` for rules.
- `Codex/agent_mode/pokemon/` — Pokemon training stack already exists
  with kenai:v1 wired in via vision + RAM-less screen capture.
- `Codex/agent_mode/factorio/` — Factorio stack already exists.
- `Codex/KENAI_v1.bat` / `KENAI_START.bat` — launcher scripts.

**How to apply:**
- Before scaffolding anything game/training related, CHECK Codex first.
  Don't write parallel work in the Claude folder.
- Corpora live at `Codex/corpora/<topic>/` — top-level, organized by
  domain (pokecrystal, factorio, cherp, code-dev all queued).
- Training datasets land in `Codex/offline_agent/brain/training/` so
  they sit next to the Modelfile iterations they feed.
- Ken AI training has THREE parallel streams: game-training (Pokemon,
  Factorio), CHERP maintenance training, code developer training. Each
  gets its own corpus folder.
- The kenai:v1 Modelfile is the consume side — corpus JSONL is what
  gets baked into the SYSTEM block (or fed to a real fine-tune via
  unsloth/axolotl).

**Outstanding remediation (2026-04-16):** Claude folder still has
duplicated `agent_mode/pokecrystal/` from a misorientation session.
Bridge.lua + ram_map.json may be worth porting to Codex's pokemon/
folder as a faster alternative to the vision-based capture. Corpus
tooling (compile_corpus.js, fetch_pokeapi.js) needs to move from
Claude side to Codex.
