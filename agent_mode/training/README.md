# Party Training Files

This folder holds editable training doctrine for the trainer and the seven P0K3M0N-inspired specialist slots.

How it works:
- `agent_mode/config/agents.json` keeps display metadata, routing fields, and the relative `charterFile` path for each slot.
- `agent_mode/core/executor.js` loads the matching charter file at prompt-build time.
- If a charter file is missing, the runtime falls back to the metadata fields in `agents.json`.

Why this exists:
- each slot can evolve independently without changing core JS
- the team can keep a strong identity per role
- Ken AI can stay the orchestrator while the party gains sharper specialist behavior over time

Editing guidance:
- keep each charter focused on one specialist role
- prefer durable instructions over task-specific notes
- update the partner language when the team shape changes
