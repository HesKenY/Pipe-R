# TASK: run evaluator against ken-ai:latest

**Created:** 2026-04-14
**Priority:** 3 (needs ollama roster + a model to eval)
**Assigned:** self (fire from cli or the API when ready)

## Goal
Fire `brain/evaluator.py ken-ai-offline-v0 --model ken-ai:latest`
and land the first real evaluation report at
`brain/training/evaluations/<ts>-ken-ai-offline-v0-ken-ai_latest.json`.

This is the baseline score for the current production Ken AI
model. Once we land `ken-ai-v1` from the Modelfile, we re-run
the evaluator against both and compare the deltas — that's
the rubric-based way to know whether the fine-tune helped.

## Steps
1. Ensure ollama is running: `ollama list | grep ken-ai:latest`
2. Ensure at least one probe per evaluation_goal matches —
   check `brain/evaluator.py PROBES` list against the 8 goals
   in `brain/model_designs/ken-ai-offline-v0/design.json`
3. Run: `python brain/evaluator.py ken-ai-offline-v0 --model ken-ai:latest`
4. Inspect report at `brain/training/evaluations/<ts>-*.json`
5. Record the overall percent + which probes failed
6. Use failing probes to decide which training rows to
   oversample in the next dataset build

## Alternative path — via API
```
python main.py &
curl -X POST "http://127.0.0.1:7778/api/model_designs/ken-ai-offline-v0/evaluate?model=ken-ai:latest"
```

## Acceptance
- Report written to `brain/training/evaluations/`
- At least 4 of 6 probes run (goals matching the probe
  keywords should all fire)
- Overall percent computed and stored
- Failed probes listed so Ken knows which areas to improve

## Why this isn't auto-run
The evaluator spawns `ollama run` which is 15-45s per probe
× 6 probes = 2-5 min per run. That's too heavy for the FastAPI
startup path — should be fired explicitly by Ken or from a
scheduled job. API endpoint is in place
(`POST /api/model_designs/<slug>/evaluate?model=<tag>`) so
the deck can fire it on demand.
