# Project Rules — Ken's offline agent

## Platform — Windows 11 Pro

Ken's machine is Windows 11 Pro. **Read `windows_rules.md`
before suggesting any shell command, file path, or subprocess
spawn.** Generic Linux advice will break — wrong slashes,
wrong kill commands, wrong env var syntax, wrong line
endings. Default to:
- Windows paths: forward slashes in code, backslashes in `.bat`
- Subprocess spawns: `creationflags=CREATE_NO_WINDOW`, `encoding="utf-8"`
- Process kill: `taskkill /PID <id> /F`, never `kill`
- Console print: ASCII only (cp1252 can't render box-drawing)
- Elevation: only when needed, always visible UAC prompt
- Paths with spaces: always quoted
- Never hardcode `C:/Users/Ken/...` — use `%USERPROFILE%` or `Path.home()`

## General Rules
- **Read before write.** Always. No exceptions. No edit without a
  prior read of the target file.
- Apply the smallest patch that solves the problem. No speculative
  refactors. No "while I'm here" cleanup unless Ken asked for it.
- Never delete a file without a backup entry in the session log.
- Commit messages: what changed + why. Lowercase, terse.
- If a test fails after a patch, revert and rethink. Do not fix
  the test to match bad code.

## Voice Rules (hard)
- lowercase only
- no "as an AI"
- no analogies, no "think of it as" / "like a"
- no construction metaphors when talking about code
- typos ok, direct action beats hedging
- 4-10 words per line for short actions

## Code Style
- Python: black + flake8. Type hints preferred.
- JS/TS: match repo style. No new deps without asking Ken.
- Comments: only when the WHY is non-obvious. Never explain
  what the code does — a reader can see that.
- No emoji in code or commit messages unless Ken explicitly asks.

## File Safety Rules
- `workspace/` — full read/write in Mode 1+
- `brain/` — read always, write in Mode 1+ (but only to add/update
  master_index files, never to delete them without Ken's go-ahead)
- `logs/` — append only
- `config/` — read only (manual edits from Ken only)
- System paths (`C:/Windows`, `C:/System32`) — never touch regardless
  of mode
- Ken's CHERP repo (`workspace/CHERP` when present) — read in
  Mode 0, write in Mode 1 with extra care (this is a LIVE production
  repo, Ken has customers on it)

## Git Rules
- Never force push to main on any repo
- Never commit to main directly WITHOUT asking Ken first, except
  for the brain/ + workspace/ of this project
- Always run tests before committing
- Commit messages: descriptive but terse. No "type(scope)"
  conventional-commit prefix required — match the repo's existing
  style (Ken's repos use plain prose subjects)
- When committing in Ken's CHERP repo, always include the
  `Co-Authored-By: Ken AI (offline)` trailer

## CHERP-Specific Rules
- `crew_tasks.id` is `BIGINT GENERATED ALWAYS AS IDENTITY` — never
  send a client id on POST, always use `Prefer: return=representation`
- `daily_logs` has NO `team_code` — uses `company_id` + `created_by`
- `messages` has NO `team_code` — uses `sender_id` + `channel`,
  content column is `body` not `content`
- `crew_timecards` uses client-generated TEXT id (not auto). Columns
  are `user_id`, `user_name`, `hours`, `date`
- `user_profiles.role` valid set (as of phase 2):
  apprentice / journeyman / foreman / general_foreman / worker /
  superintendent / admin / superuser
- The app writes JSA to `crew_jsa` not `jsa_reports`, and MROs to
  `crew_mros` not `mro_equipment`
- Offline-first: CHERP routes through `window.store` (IndexedDB
  read-through cache + write-through queue). Direct Supabase writes
  only as fallback

## Halo-Trainer Rules (sibling project at `../halo-trainer/`)
- Drills bypass the orchestrator SYSTEM prompt wrapper — spawn
  ollama directly so responses don't drift into role persona
- Rubrics are the source of truth for "good." If a drill scores
  low, update the rubric before tuning the prompt
- Only drills that pass their `passingPercent` threshold land in
  `corpus/<curriculum>.jsonl`
- Curated corpus is the Ken AI v2 fine-tune dataset

## Task Rules
- Every task produces a session log entry in `brain/sessions/`
- Completed tasks move from `tasks/open/` to `tasks/done/`
- Blocked tasks get a `blocked` entry with the reason
- Ambiguous tasks → ask before proceeding, don't guess

## Escalation Rules
- Task requires Mode 2 or higher → pause, show the mode escalation
  dialog, wait for Ken's confirmation
- Kill switch file exists at `config/.kill_switch` → halt IMMEDIATELY,
  no cleanup write-out, no "just one more thing"
- Any tool returns an unexpected error → stop, log, ask Ken before
  retrying (don't retry-loop silently)
- Detected a system-level change (startup item, service, registry) →
  full stop, regardless of mode
