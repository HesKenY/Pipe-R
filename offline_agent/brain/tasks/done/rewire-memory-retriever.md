# TASK: rewire memory_retriever for brain_index layout

**Created:** 2026-04-14
**Priority:** 1 (blocking everything else — planner can't
load context until this ships)
**Assigned:** self

## Goal
Update `agent_core/memory_retriever.py` to read the new brain
layout (`brain_index/` + `sessions/YYYY-MM-DD/` + `tasks/`) and
rebuild the SQLite FTS tables to match.

## Acceptance criteria
- `memory_retriever.py` indexes `brain/brain_index/*.md` instead
  of `brain/master_index/*.md`
- Session FTS indexes all files under `brain/sessions/**/*.md`
  (walks the YYYY-MM-DD subdirs)
- New FTS table `task_fts` indexes `brain/tasks/{open,done}/*.md`
  so queries like "what's in flight" return open tasks
- `get_relevant_context(task)` still returns identity + rules
  as baseline context always, plus top-K chunks from the FTS
  search + last session log tail
- `_index_brain()` becomes `_rebuild_index()` and rebuilds all
  three FTS tables in one pass
- Smoke test: start the server, `GET /api/brain` returns the
  6 new brain_index files

## Out of scope for this task
- brain_build.py (separate task)
- Claude log ingestion (separate task)
- Session log auto-summarization (separate task)
