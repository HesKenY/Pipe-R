# TASK: smoke-test the FastAPI boot

**Created:** 2026-04-14
**Priority:** 3 (can wait, brain is usable without it)
**Assigned:** self

## Goal
Start `main.py`, confirm it binds to 127.0.0.1:7778 cleanly,
hit `/api/status` and `/api/brain`, verify the planner loop
can load baseline context for a trivial task.

## Steps
1. `pip install -r requirements.txt`
2. `python main.py`
3. `curl http://127.0.0.1:7778/api/status`
4. `curl http://127.0.0.1:7778/api/brain`
5. Via WebSocket or API: dispatch a trivial task like
   "list the brain files" and confirm the planner's
   context assembly + tool routing works end-to-end
6. Hit Ctrl+C, confirm clean shutdown

## Acceptance
- status endpoint returns `"agent": "Ken AI offline v0.1.0-skeleton"`
- brain endpoint lists 9+ brain_index files
- no exceptions in the server log at boot
- Ctrl+C exits cleanly

## Notes
- Port 7778, NOT 7777 (Pipe-R owns 7777)
- Requires Ollama running at 127.0.0.1:11434
- Should work even if no model is loaded yet — just the
  status + brain endpoints are needed for this smoke test

## Known risks
- `tools/ui_tools.py` imports pyautogui which may not be
  installed — Mode 0 smoke test should still boot since
  tool registration is lazy, but check
- `requirements.txt` may need pyyaml added (we just installed
  it manually)
