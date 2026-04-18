# Party Training Files

This folder holds training doctrine, corpus builders, and fine-tune
inputs for Ken V4 offline developer and the supporting specialist slots.

How it works:
- `agent_mode/config/agents.json` keeps display metadata, routing fields, and the relative `charterFile` path for each slot.
- `agent_mode/core/executor.js` loads the matching charter file at prompt-build time.
- If a charter file is missing, the runtime falls back to the metadata fields in `agents.json`.

Why this exists:
- each slot can evolve independently without changing core JS
- the team can keep a strong identity per role
- the default corpus can stay coding-first even if older game-era data still exists in the repo

Important corpus direction:
- Ken V4 offline developer is the primary target
- default corpus should over-weight coding, repo safety, verification, tool JSON, and local Windows workflows
- Halo / Factorio / Pokemon-era data is archived context, not the default training center anymore

Useful files:
- `corpus_builder_v4.mjs` — deterministic curated coding-first pairs for V4
- `export_kenai_v4_dataset.mjs` — combines curated pairs + approved coding rows into `kenai-v4-finetune.jsonl`
- `kenai-v4-curated-corpus.jsonl` — generated curated corpus rows
- `kenai-v4-finetune.jsonl` — generated fine-tune dataset in `messages` JSONL format

Editing guidance:
- keep each charter focused on one specialist role
- prefer durable instructions over task-specific notes
- update the partner language when the team shape changes
