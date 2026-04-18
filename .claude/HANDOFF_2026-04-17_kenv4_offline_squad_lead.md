# HANDOFF — 2026-04-17 — ken v4 offline squad lead

## Summary

`offline_agent` has been reworked around **Ken V4 Offline Developer**
as the **coding-first lead of the local agent squad**.

This now goes beyond the earlier read-only bridge. The offline workbench
and the live `agent_mode` runtime are both wired to
`kenai:v4-offline-developer` as the canonical squad lead, with runtime
compatibility fallback to `ken-ai:latest`.

No commit was made yet.

---

## What shipped locally

### offline_agent runtime

- `offline_agent/main.py`
  - version bumped to `0.4.1`
  - `workbench_snapshot()` now includes squad state
  - new `GET /api/squad`
- `offline_agent/agent_core/squad_state.py`
  - new read-only bridge into:
    - `agent_mode/config/agents.json`
    - `agent_mode/config/runtime.json`
    - `agent_mode/config/tasks.json`
  - computes:
    - intended lead
    - runtime lead
    - sync state
    - roster health
    - pending queue
- `offline_agent/agent_core/planner.py`
  - system prompt now treats KenAI as the **coding-first squad lead**
  - planner gets compact squad context each turn
  - explicit rule: do not mutate live `agent_mode/config/*.json`
    unless Ken explicitly asks

### offline_agent UI

- `offline_agent/frontend/index.html`
  - new **Squad Lead** panel
  - shows:
    - intended lead
    - runtime lead
    - sync state
    - alerts
    - roster
    - queue
  - startup/status copy now matches the squad-lead direction

### config + docs alignment

- `offline_agent/config/projects.yaml`
  - now declares:
    - `agent_mode` as a first-class read-only project
    - `lead_model: kenai:v4-offline-developer`
- `offline_agent/config/models.yaml`
  - planner description updated to squad-lead framing
- updated docs/brain references:
  - `offline_agent/README.md`
  - `offline_agent/brain/model_designs/ken-ai-offline-v0/design.json`
  - `offline_agent/brain/brain_index/identity.md`
  - `offline_agent/brain/brain_index/rules.md`
  - `offline_agent/brain/brain_index/project_map.md`
  - `offline_agent/brain/brain_index/repo_map.md`
  - `offline_agent/brain/brain_index/tech_stack.md`

### live agent_mode trainer wiring

- `agent_mode/core/trainer_identity.js`
  - new canonical trainer identity + alias helpers
- `agent_mode/core/registry.js`
  - canonical trainer id is now `kenai:v4-offline-developer`
  - legacy `ken-ai:latest` resolves to the same trainer
  - trainer model fallback chain is now explicit
- `agent_mode/core/executor.js`
  - trainer tasks resolve to the first available trainer model
  - training rows now stamp `agentId` and actual run model
- `agent_mode/core/orchestrator.js`
  - runtime defaults, dashboard mapping, and task refs normalize to the
    V4 trainer id
- `agent_mode/core/memory.js`
  - canonical trainer keeps using the existing `ken-ai-latest` memory dir
    when that legacy folder already exists
- `agent_mode/core/livetest.js`
  - v1 trainer slot now points at the V4 trainer id
- `agent_mode/core/stats.js`
  - trainer stats now aggregate across legacy + canonical trainer ids
- `agent_mode/config/runtime.json`
  - `trainerAgentId` now points at `kenai:v4-offline-developer`
- `agent_mode/config/agents.json`
  - canonical trainer roster row updated to V4 with fallback models

---

## Verified

### compile

- `python -m compileall offline_agent` passed

### direct squad snapshot

Observed from the new squad bridge:

- intended lead: `kenai:v4-offline-developer`
- runtime lead: `kenai:v4-offline-developer`
- sync state: `aligned`
- agents total: `8`
- queue rows returned: `6`

### trainer compatibility

- `registry.getById('ken-ai:latest')` resolves to
  `kenai:v4-offline-developer`
- `registry.resolveRunModel(primaryTrainer)` currently resolves to
  `ken-ai:latest` on this machine because that tag exists locally
- `memoryDir('kenai:v4-offline-developer')` still lands on the existing
  `agent_mode/memories/ken-ai-latest` folder, so Ken's trainer notes/logs
  stay intact

### live HTTP smoke test

`GET http://127.0.0.1:7778/api/workbench` returned:

- `KenAI Offline Developer 0.4.1`
- intended lead `kenai:v4-offline-developer`
- runtime lead `kenai:v4-offline-developer`
- sync state `aligned`
- `agents_total = 8`

---

## What Claude should do next

The live promotion is done. The next logical pass is cleanup and
hardening, not another identity swap.

### recommended next checks

1. Decide whether open rows in `agent_mode/config/tasks.json` that still
   reference `ken-ai:latest` should be rewritten to the canonical trainer
   id or left as historical alias-compatible rows.
2. Decide whether the trainer memory folder should stay on the legacy
   slug (`memories/ken-ai-latest`) or get a careful migration to a new
   canonical folder later.
3. If Ken builds the true `kenai:v4-offline-developer` Ollama tag, verify
   that `registry.resolveRunModel()` flips from fallback to the V4 tag
   without breaking dispatch, dashboard state, or training stats.
4. If desired, update remaining docs under `agent_mode/ken/` to reflect
   the V4 naming more explicitly.

---

## Dirty-tree note

There are already many unrelated dirty changes elsewhere in the repo.
I did not revert any of them.

For this handoff, the relevant files touched are:

- `offline_agent/main.py`
- `offline_agent/agent_core/planner.py`
- `offline_agent/agent_core/squad_state.py`
- `offline_agent/frontend/index.html`
- `offline_agent/config/projects.yaml`
- `offline_agent/config/models.yaml`
- `offline_agent/README.md`
- `offline_agent/brain/model_designs/ken-ai-offline-v0/design.json`
- `offline_agent/brain/brain_index/identity.md`
- `offline_agent/brain/brain_index/rules.md`
- `offline_agent/brain/brain_index/project_map.md`
- `offline_agent/brain/brain_index/repo_map.md`
- `offline_agent/brain/brain_index/tech_stack.md`

---

## Bottom line

Ken V4 offline developer now **looks and behaves like the intended
coding-first squad lead** inside `offline_agent`.

What is still pending is cleanup around the now-promoted trainer id, not
the promotion itself.
