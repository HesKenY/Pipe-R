# Project Rules - Ken's offline developer agent

## Platform
- Windows first
- use Windows-safe paths and commands
- prefer ASCII output in console-facing surfaces
- quote paths with spaces

## General Rules
- read before write
- smallest patch that solves the task
- no speculative refactors unless Ken asks
- back up before destructive edits
- test after code changes when a test path exists
- keep notes in the brain when the context matters later

## Safety Rules
- never touch system paths or secrets
- never force-push main
- never run destructive shell commands
- never write into `C:/Users/Ken/Desktop/Claude`
- mode 0 stays read-only
- kill switch always wins

## Repo Rules
- Codex is the active workspace
- the Claude folder is a peer clone, not a write target
- use git to sync shared state between clones
- respect existing dirty worktrees and do not revert unrelated work

## Code Rules
- Python: black-style formatting and simple type hints when useful
- JS/TS: match repo style, no new deps without asking
- comments explain why, not what
- keep UI button-driven where the project already expects it

## CHERP Rules
- treat CHERP as production-sensitive
- preserve offline-first flows
- do not invent schema columns
- read the existing store and schema paths before changing behavior

## Task Rules
- every task should have a session trace
- open tasks live in `brain/tasks/open`
- completed tasks move to `brain/tasks/done`
- blocked tasks should record why they stopped

## Model Direction
- Ken V4 offline developer is the target
- Ken V4 offline developer leads the local agent squad from the coding workbench
- keep corpus and runtime focused on coding, brain retrieval, git, tests, and safe local execution
- do not reintroduce game-first behavior into the default runtime
- read `agent_mode` squad state by default; do not rewrite live squad config unless Ken explicitly asks
