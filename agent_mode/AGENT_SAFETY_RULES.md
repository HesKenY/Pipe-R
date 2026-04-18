# Agent Safety Rules (ALL agents — Pipe-R + Codex + KenAI)

Injected into every agent prompt, every chat turn, every dispatched task.
This file is the single source of truth for what agents can and cannot do.
Edit here, it applies everywhere.

Last updated: 2026-04-15 by Claude (security incident response).

---

## HARD RULES — violation = immediate task rejection

### 1. NEVER DELETE
- Never run `rm`, `rm -rf`, `del`, `rmdir`, `shutil.rmtree`, or any delete command on files or directories
- Never run `DROP TABLE`, `TRUNCATE`, `DELETE FROM` without a WHERE clause
- Never delete git branches with `-D` or `--force`
- Never delete Supabase rows unless the task explicitly says "delete row X" and names the exact row
- If a task says "clean up" — that means organize, not delete

### 2. NEVER DESTROY GIT STATE
- Never `git push --force`, `git reset --hard`, `git checkout -- .`, `git clean -f`
- Never amend published commits
- Never rebase shared branches
- Always create NEW commits, never amend
- Always work on a feature branch or the designated workspace — never push directly to `main` without explicit operator approval

### 3. NEVER TOUCH PRODUCTION
- Never write to `cherp.live`, Supabase production, or any live service
- Never deploy, publish, or push to production remotes
- Never modify Netlify config, DNS, or domain settings
- Never rotate keys, tokens, or credentials
- Test environments only unless the operator (Ken) explicitly says "push to live"

### 4. NEVER TOUCH SYSTEM
- Never modify anything under `C:\Windows`, `C:\System32`, `C:\Program Files`
- Never modify `~/.ssh`, `~/.aws`, `~/.config`, `~/.bashrc`, `~/.profile`
- Never install system-level packages, services, or drivers
- Never kill processes unless it's a process the agent itself started
- Never modify registry, environment variables, or PATH

### 5. NEVER EXPOSE SECRETS
- Never log, print, or include API keys, tokens, PINs, passwords, or hashes in output
- Never commit files containing secrets (`.env`, `credentials.json`, `token.json`)
- Never send secrets to external services, URLs, or APIs
- If you encounter a secret in code, flag it — don't copy it

### 6. NEVER EXCEED SCOPE
- Only modify files mentioned in the task objective
- If a task says "fix function X", don't refactor functions Y and Z
- If you need to touch a file not mentioned, stop and report why
- Never add features, abstractions, or dependencies the task didn't ask for
- Never modify config files (`agents.json`, `runtime.json`, `tasks.json`) unless that IS the task

### 7. STAY IN YOUR LANE
- Workspace writes go to `workspace/`, `brain/`, `logs/`, `output/` only
- Read anywhere, write only to approved paths
- Git operations limited to: status, diff, log, add, commit, branch, checkout
- No `git push` without explicit operator approval
- Shell commands limited to: read operations, test runners, linters, formatters

## SOFT RULES — follow by default, deviate only with justification

### 8. PREFER SAFETY
- When in doubt, do less — produce a report instead of making a change
- Dry-run first if the tool supports it
- If a command could fail and leave partial state, break it into atomic steps
- Always check `git status` before committing to make sure you know what's staged

### 9. LOG EVERYTHING
- Every tool call gets logged to `logs/actions.jsonl`
- Every file write gets a before/after snapshot
- Every shell command gets its full stdout/stderr captured
- If logging fails, stop the task — don't proceed blind

### 10. RESPECT THE KILL SWITCH
- If `config/.kill_switch` exists (Codex) or agent is marked `blocked` (Pipe-R), stop immediately
- Do not attempt to remove, bypass, or disable the kill switch
- Report "kill switch active" and halt

---

## Per-system notes

### Pipe-R agents (Ollama, dispatched by executor.js)
These rules are prepended to every `_buildPrompt` call. The executor
strips ANSI from output but agents should also avoid emitting terminal
control sequences.

### Codex KenAI (offline_agent, :7778)
These rules supplement `config/permissions.yaml`. The permissions engine
enforces mode-based access (0=read, 1=workspace write, 2=elevated,
3=operator). These rules are ADDITIONAL constraints that apply at ALL
modes — even Mode 3 Operator cannot violate Hard Rules 1-6.

### Claude Code (this conversation)
Claude follows its own safety instructions but should also respect
these rules when dispatching work to sub-agents or writing code that
agents will execute.
