# HANDOFF — 2026-04-18 — pre-Linux migration snapshot

## Summary

Ken is setting up a dual-boot **Pop!_OS 22.04 (NVIDIA iso)** install on a
separate drive today. Linux will be the new dev playground for Codex +
CHERP + Kenai work. Windows stays intact for Halo/gaming/deck side.

This commit is the **pre-migration snapshot** so the Linux clone starts
from a real HEAD rather than stale `origin/main`. Nothing in-progress is
being abandoned — it's all committed as-is.

---

## What this commit contains

Large bundle (~212 files). Logical buckets:

### 1. Ken V4 offline squad lead promotion (per 2026-04-17 handoff)
- `offline_agent/main.py`, `squad_state.py`, `planner.py`
- `offline_agent/frontend/index.html` — Squad Lead panel
- `offline_agent/config/projects.yaml`, `models.yaml`
- `offline_agent/brain/brain_index/*.md` — identity/rules/project_map/repo_map/tech_stack
- `offline_agent/brain/model_designs/ken-ai-offline-v0/design.json`
- `offline_agent/README.md`
- `agent_mode/core/trainer_identity.js` (new)
- `agent_mode/core/registry.js`, `executor.js`, `orchestrator.js`, `memory.js`, `livetest.js`, `stats.js`
- `agent_mode/config/agents.json`, `runtime.json`
- Canonical trainer id is now `kenai:v4-offline-developer` with fallback to `ken-ai:latest`

### 2. Halo trainer classroom (halo-trainer/)
- Drills: recon 101/102, reverse 101/102, implementation 101, trainer 101/102
- `src/registry.js`, `runner.js`
- `WALKTHROUGH.md`
- Scored exercises feeding curated rows → future Ken AI v2 fine-tune

### 3. Halo live loop (agent_mode/halo/)
- `agent.js`, `halo_squad.js`, `halo_tick.py`
- `post_mortem.js`, `train_pass.js`, `trainer.js`, `training_mode.js`
- Death-watch + auto-train pipeline (per commits c6ce03a, 7ff079f)

### 4. Offline agent brain rebuild (offline_agent/)
- `agent_core/*.py` — memory_retriever, patch_engine, permissions, planner, session_manager
- `brain/*.py` — evaluator, model_designer, modelfile_builder
- `brain/import_manifest.yaml`, `config/models.yaml`
- `brain/sessions/2026-04-14/*.md`
- `START.bat`

### 5. Misc WIP
- `.claude/CODEX_BRIEF.md` — minor sync tweaks

### 6. Claude auto-memory snapshot (NEW in this commit)
- `.claude/archive/pre-linux-memory-snapshot/` — 32-file snapshot of
  Claude-side auto-memory (`C:\Users\Ken\.claude\projects\C--Users-Ken-Desktop-Claude\memory\`)
  preserved in-repo so the Linux clone has full context without needing
  to port the OS-level memory folder. Files dated through 2026-04-16.

---

## ⚠️ Claude-side coordination note

At snapshot time the Claude clone at `C:\Users\Ken\Desktop\Claude` is:
- **5 commits behind `origin/main`** (hadn't pulled V4 corpus + Halo tab work)
- **16 dirty files** (4 modified + 12 untracked)

### Collisions — will hit Claude on next `git pull`

Two files overlap between this commit and Claude's local dirty tree:

1. `agent_mode/config/agents.json`
2. `agent_mode/memories/ken-ai-latest/halo-memory.md`

**Resolution guidance for Claude side:**
- `git stash` the 16 dirty files first
- `git pull` to get up to date (HEAD will move to this snapshot commit)
- `git stash pop` — will conflict on the 2 files above
- Manual merge: Codex's version brings V4 trainer canonical id + halo-memory snapshot from Codex's side. Claude's dirty likely has overlapping halo session data. Keep both → merge by union where possible.
- Re-commit the resolved delta and push

Claude's untracked files (halo-events.jsonl, halo-keylog.jsonl, halo-jumpstart.json, halo-reverse.md, halo2-dll-entry-points.md, poke-memory.md, `_halo_prev_frame.png`, `halo_training.json`) are fresh additions with no Codex-side equivalent — just `git add` and include in the next commit.

---

## What Linux-side Claude should do on first boot

1. Clone the repo to `~/Codex` (or agreed path)
2. Read these files in this order:
   - `CLAUDE.md` — project overview
   - `AGENTS.md` — coordination protocol
   - `.claude/CODEX_BRIEF.md` — Ken profile + voice + design rules
   - `.claude/archive/pre-linux-memory-snapshot/MEMORY.md` — index of the ported auto-memory
   - This handoff (`HANDOFF_2026-04-18_pre-linux-migration.md`)
3. Rehydrate OS-level memory from the archive snapshot — copy into
   `~/.claude/projects/<slug>/memory/` or let Claude rebuild from the
   archived files as it sees fit
4. Start bootstrap: Node, Python, Ollama, gh, Chrome, VS Code, Tailscale, plus the Pop!_OS gaming layer (Steam + Proton-GE + Lutris + Mesa PPA + MangoHud + GameMode)
5. Re-pull Ollama models per inventory (clean re-pull strategy — not physical copy from NTFS)

---

## Target distro

**Pop!_OS 22.04 LTS (NVIDIA iso)**. Locked after a quick Nobara detour
for gaming compat. Gaming layer gets installed manually via script on
first boot so Ken's Steam library (GTA V primary) runs via Proton-GE.

---

## Bottom line

Snapshot is clean. Linux Claude inherits the full project state plus a
preserved auto-memory archive. Claude-side Windows clone needs one
careful pull + merge on the 2 collision files before it resumes work.
