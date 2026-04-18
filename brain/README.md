# BRAIN Repository

BRAIN is the first-rule repository for the new deck iteration.

It has four jobs:

1. Ingest project memory, logs, dreams, learning artifacts, and branch state from every approved workspace.
2. Expose a searchable compendium for local and cloud AI context building.
3. Persist model-design blueprints for the proprietary offline developer model we are building.
4. Act as the controller layer behind the deck's BRAIN tab and Ken AI chat workflow.

Core files:

- `build_brain.py` - multi-repository ingest and indexing into `BRAIN.db`
- `query_brain.py` - search and context pack queries for deck and build agents
- `export_dataset.py` - exports BRAIN dataset slices into `brain/exports/`
- `repositories.json` - approved roots that BRAIN is allowed to ingest
- `BRAIN_CHARTER.md` - operating rules and logging requirements
- `MODEL_DESIGNER_SPEC.md` - design intent for the new proprietary model
- `designs/` - saved model blueprints emitted from the deck
- `training_specs/` - BRAIN-backed training specifications for model runs

Current approved repositories:

- `codex` -> `C:\Users\Ken\Desktop\Codex`
- `codex_source_main` -> `C:\Users\Ken\Desktop\Codex\input\Codex-source-main`
- `claude_import` -> `C:\Users\Ken\Desktop\Codex\input\Claude-import`

`source_mirror` repositories are scanned recursively for scrubbed text/code
artifacts so imported source mirrors can be queried from BRAIN without turning
them into primary execution roots.

Build:

```powershell
python brain\build_brain.py --json
```

Query:

```powershell
python brain\query_brain.py status
python brain\query_brain.py search "ken ai chat" --limit 8
python brain\query_brain.py context "brain controller" --repo codex --target local
```

Export:

```powershell
python brain\export_dataset.py --json --name "Ken AI Offline Developer" --query "ken ai chat" --repo codex --limit 50
```
