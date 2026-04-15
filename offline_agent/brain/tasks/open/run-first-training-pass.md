# TASK: run first real training pass

**Created:** 2026-04-14
**Priority:** 1
**Assigned:** self + Ken

## Goal
Take the `ken-ai-offline-v0` model design all the way from
draft → dataset → training spec → evaluation plan, ready for
Ken to kick off an actual Ollama fine-tune when the corpus
is big enough.

## Current state (2026-04-14 20:20)
- `ken-ai-offline-v0` design validates 9/9
- First dataset build: 32 records
  - halo-trainer corpus: 5 curricula imported, ~15 passing rows
  - pipe-r approved dispatches: ~10 rows
  - session logs last 30 days: ~2 files
  - brain_index reference: 10 files
- Training spec written to `brain/training/specs/`
- Dataset is Codex-schema compatible (matches
  `Codex/brain/training_specs/*.json`)

## What needs to happen before we train
1. Grow the corpus — 32 rows is too few. Target: 150+
   clean rows before any real fine-tune
2. Run halo-trainer at least 3 more times to generate more
   passing drill rows
3. Dispatch ~20 more ken-ai:latest tasks via Pipe-R so the
   training-log has more approved dispatch rows
4. Auto-approve Ken-voice rows only (filter by
   `model == ken-ai:latest AND success == true`)
5. Dedupe near-identical rows (common with similar drill
   retries)

## Steps when we're ready
1. `python brain/brain_build.py --once` — refresh imports
2. `python brain/model_designer.py full ken-ai-offline-v0`
3. Inspect dataset at `brain/training/datasets/<ts>-ken-ai-offline-v0.jsonl`
4. Convert to Ollama Modelfile format (messages array →
   SYSTEM + FROM base)
5. `ollama create ken-ai-v1 -f <Modelfile>`
6. Smoke test: ollama run ken-ai-v1 "say hi in your own voice"
7. Move design status from `draft` → `training` → `evaluating`
8. Ken runs the evaluation goals checklist manually
9. Status → `deployed` if it passes

## Acceptance
- 150+ record dataset built
- Valid training spec matching Codex schema
- Ollama model created locally
- At least one successful smoke test on the new model
- Design moved to `evaluating` or `deployed` status

## Notes
- Do NOT train on rows tagged `model != ken-ai:latest` unless
  the response is structured JSON / code (voice drift risk)
- Session-log narrative is useful for context but should be
  a MINORITY of the corpus — aim for 3:1 ken-voice:narrative
- Keep rollback easy — don't replace `ken-ai:latest`, create
  `ken-ai-v1` as a new tag until Ken approves
