---
name: Codex BRAIN repository system
description: Top-level BRAIN at Codex/brain/ is the multi-repo indexer + dataset emitter for the offline model
type: reference
originSessionId: 4f2069d0-f62b-4932-beb3-48c801257e56
---
The `brain/` folder at the top of `C:\Users\Ken\Desktop\Codex\` is a
multi-repo ingest + indexing system that backs:
- the deck's BRAIN tab (search across all approved repos)
- Ken AI chat workflow (context retrieval)
- model-design blueprints (saved to `brain/designs/`)
- training-dataset slicing (emitted to `brain/exports/`)

**Files:**
- `build_brain.py` — ingest + index into `BRAIN.db` (SQLite)
- `query_brain.py` — search and context-pack queries
- `export_dataset.py` — export dataset slices for training
- `repositories.json` — APPROVED roots BRAIN may ingest (gate)
- `BRAIN_CHARTER.md` — operating rules and logging requirements
- `MODEL_DESIGNER_SPEC.md` — design intent for the offline model

**Approved repos as of 2026-04-16:**
- `codex` → `C:\Users\Ken\Desktop\Codex`
- `codex_source_main` → `C:\Users\Ken\Desktop\Codex\input\Codex-source-main`
- `claude_import` → `C:\Users\Ken\Desktop\Codex\input\Claude-import`

**Build / query / export commands:**
```powershell
python brain\build_brain.py --json
python brain\query_brain.py status
python brain\query_brain.py search "ken ai chat" --limit 8
python brain\query_brain.py context "brain controller" --repo codex --target local
python brain\export_dataset.py --json --name "..." --query "..." --repo codex --limit 50
```

**Logging standard for agents working in Codex:**
- `.claude/logs/codex.log`
- `.claude/logs/shared.log`
- `.claude/SESSION_LOG.md`
- `.claude/MEMORY_INDEX.md`

**Distinction from `offline_agent/brain/`:** Top-level `brain/` is the
INDEX/DATASET layer. `offline_agent/brain/training/` is where the
trained-model artifacts (Modelfiles, unsloth JSONL) live. Don't
confuse them.
