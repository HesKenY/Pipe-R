# Repo Map

## Git identity
- user: HesKenY
- name: Ken

## Primary remotes
- `origin` -> `https://github.com/HesKenY/CHERP-Backup.git`
- `pipe-r` -> `https://github.com/HesKenY/Pipe-R.git`
- `cherp` -> `https://github.com/HesKenY/CHERP.git`
- `nest` -> `https://github.com/HesKenY/CHERP-Nest.git`

## Clones on disk

### Codex
- path: `C:/Users/Ken/Desktop/Codex`
- role: active workspace for Codex and offline_agent
- write target: yes

### Claude
- path: `C:/Users/Ken/Desktop/Claude`
- role: peer workspace for the Claude agent
- write target: no, not from offline_agent

### CHERP working copy
- path: `C:/Users/Ken/Desktop/Codex/workspace/CHERP`
- role: live product repo
- write target: only with care and verification

## Coordination rules
- both agent worktrees sync through git
- do not edit the Claude clone directly from this runtime
- do not force-push shared repos
- do not revert unrelated dirty worktree changes
- treat `agent_mode/config/*.json` as shared live squad state; read by default and edit only when Ken explicitly wants a live promotion
- read `AGENTS.md`, `CLAUDE.md`, and `.claude/CODEX_BRIEF.md` at session start when the context matters
