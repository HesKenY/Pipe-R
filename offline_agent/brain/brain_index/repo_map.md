# Repo Map — where every git repo lives on Ken's machine

## Git identity
- **User:** HesKenY on GitHub
- **Name:** Ken
- **Commits should include** `Co-Authored-By: Ken AI (offline) <noreply@hesken.dev>`
  trailer when this offline agent is the one authoring the change

## Remotes in use
- **origin** → `https://github.com/HesKenY/CHERP-Backup.git`
  — primary. Every CHERP + Pipe-R + halo-trainer commit lands
  here. Shared between Claude and Codex clones.
- **pipe-r** → `https://github.com/HesKenY/Pipe-R.git`
  — secondary. Mirrored pushes for the Pipe-R part of the
  shared repo.
- **cherp** → `https://github.com/HesKenY/CHERP.git`
  — for the CHERP-only working copy when cloned separately.
  Private.
- **nest** → `https://github.com/HesKenY/CHERP-Nest.git`
  — Bird's Nest instance manager
- **cmc** → `https://github.com/HesKenY/CMC.git`
  — Clean Money Corporation / ACE rebrand
- **codeforge** → `https://github.com/HesKenY/CodeForge.git`

## Clones on disk (Windows paths)

### Claude parallel clone
- **Path:** `C:/Users/Ken/Desktop/Claude/`
- **Owner:** Claude (Anthropic Claude Code CLI)
- **Role:** Claude's working copy. Claude edits here.
- **Do not touch from offline_agent** unless explicitly
  delegated a task that crosses clones. Read-only by default.
- **Remotes:** origin + pipe-r

### Codex parallel clone
- **Path:** `C:/Users/Ken/Desktop/Codex/`
- **Owner:** Codex (OpenAI Codex CLI) + offline_agent (this project)
- **Role:** shared workspace. Codex edits outside `halo-trainer/`
  and `offline_agent/`. offline_agent lives inside and can edit
  its own subtree freely.
- **Remotes:** origin + pipe-r
- **Subdirs this agent owns:**
  - `offline_agent/` — this project
  - `halo-trainer/` — sibling classroom (Claude also touches
    this, use commit-level coordination via AGENTS.md)
- **Subdirs this agent READS but does not write:**
  - `agent_mode/` — Pipe-R's agent runtime
  - `hub.js`, `server.js`, `pipe-r.html` — Pipe-R core

### CHERP working copy (when cloned locally)
- **Path:** `C:/Users/Ken/Desktop/Codex/workspace/CHERP`
  (or equivalent under `workspace/`)
- **Owner:** shared. Ken, Claude, Codex all touch this
- **Role:** the live CHERP codebase. LIVE on cherp.live via Netlify
- **Touch protocol:** read always, write only after running the
  local test harness (`node test/run-all.js`) AND only on `dev`
  branch. PRs to `main` get Ken's approval first.

## Branches
- **main** — the deploy branch. cherp.live deploys from here.
  Force-push is forbidden on all repos
- **dev** — CHERP's staging branch. Phase work lands here first
  then merges to main after Ken smoke-tests
- Feature branches — rare. Ken's normal flow is "commit small
  and often on main, revert if it breaks"

## Parallel-agent coordination
See `C:/Users/Ken/Desktop/Codex/AGENTS.md` for the full
protocol. Short version:
- Both Claude and Codex push to the same `origin`. Rebase,
  don't merge, to stay linear
- Before starting non-trivial work, read the most recent
  `.claude/HANDOFF_*.md` for context
- Log events to `.claude/logs/shared.log` (one line per
  event, both agents write)
- offline_agent is a THIRD agent and stays inside
  `Codex/offline_agent/` and `Codex/halo-trainer/` to avoid
  collisions with Claude + Codex

## Critical files (do not corrupt)
- `.git/` in both clones — obvious
- `agent_mode/training/training-log.jsonl` — the fine-tune
  corpus. Append-only, never rewrite history
- `agent_mode/config/tasks.json` — held in-memory by Pipe-R
  server. Stop server before editing this file directly
- `agent_mode/config/agents.json` — registry of the 8
  enrolled models
- `runtime.json` — Pipe-R's live mode state
- `cherp-schema.sql` — master Supabase schema, authoritative
- `CLAUDE.md` (in both clones) — project brief. Both agents
  read at session start
