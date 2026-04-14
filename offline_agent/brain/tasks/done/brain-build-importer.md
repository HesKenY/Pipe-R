# TASK: brain_build.py — import external context into brain

**Created:** 2026-04-14
**Priority:** 2 (after memory_retriever rewire)
**Assigned:** self

## Goal
Write `brain/brain_build.py` that periodically imports
external context into the brain so the agent has current
information without a manual copy step.

## Sources to import

| source path | destination | cadence |
|---|---|---|
| `../../agent_mode/memories/ken-ai-latest/notes.md` | `brain_index/ken_voice_profile.md` | on rebuild |
| `../../agent_mode/training/training-log.jsonl` | `training/training-log.jsonl` (sampled last 500 rows) | daily |
| `../../halo-trainer/corpus/*.jsonl` | `corpus/halo-trainer-*.jsonl` | on rebuild |
| `../../.claude/HANDOFF_*.md` | `sessions/<date>/claude-handoff-<topic>.md` | on rebuild |
| `../../.claude/logs/shared.log` | `sessions/<date>/shared-events.log` (tail 200) | on rebuild |
| `../../CLAUDE.md` | `brain_index/claude_project_brief.md` | on rebuild |

## Design
- Reads an `import_manifest.yaml` listing source → dest pairs
  with cadence hints
- Each import is idempotent: re-running doesn't duplicate
  content, just overwrites the dest file
- Writes a `brain/import_log.jsonl` row per import with
  timestamp + byte count + source path
- After every import, triggers a full FTS rebuild by calling
  the memory_retriever's `_rebuild_index()` helper
- Safe to run while the server is up — takes an advisory
  lock on `brain/import.lock`

## Smoke test
- Run `python brain/brain_build.py --once`
- Check `brain/brain_index/claude_project_brief.md` exists
- Check `brain/corpus/halo-trainer-integration.jsonl` exists
  if halo-trainer has run at least one passing integration
  drill
- Check `brain/import_log.jsonl` has a row per successful
  import

## Out of scope
- Anything that writes back to the source (this is read-only
  from all source repos)
- Network imports (no hitting GitHub, no hitting cherp.live)
- Transcoding — copy files as-is, never transform
