---
description: Memory maintenance + commit + push across Claude project and any in-workspace CHERP clone
---

# /save — checkpoint this session

Run the full "save everything" workflow in order. This is the end-of-session
button. Skip nothing. If a step fails, stop and report — don't auto-fix unless
it's a clear re-run.

## 1. Update CLAUDE.md with what shipped this session

Read `C:/Users/Ken/Desktop/Claude/CLAUDE.md` and check whether it reflects
everything that landed in this session:

- New files created (read recent git log: `git log --oneline -20`)
- Architecture changes (new endpoints, new modules, new schemas)
- Bug fixes that changed a documented behavior
- Any new section headings needed for features shipped
- Known issues/gotchas discovered this session

If anything is missing or stale, edit `CLAUDE.md` to bring it current. Keep
the existing voice (terse, technical, directive). Do NOT rewrite sections
that are still accurate. Do NOT invent content — only document what actually
shipped, with file paths + commit SHAs when they help.

## 2. Update auto-memory

Re-read `C:/Users/Ken/.claude/projects/C--Users-Ken-Desktop-Claude/memory/MEMORY.md`
and the memory files it points to. For this session specifically:

- Save any new **user** facts Ken revealed (role, preferences, knowledge)
- Save any new **feedback** rules (things Ken corrected or confirmed — watch
  for quiet confirmations, not just loud corrections)
- Save any new **project** facts (decisions, ownership changes, in-flight work
  that will be relevant next session)
- Save any new **reference** pointers (external systems, dashboards, repos)
- Update existing memory files that got more accurate info
- Remove anything that turned out to be wrong

Every new memory gets a pointer in `MEMORY.md` (one line, under 150 chars).

## 3. Commit + push the Claude project repo

From `C:/Users/Ken/Desktop/Claude`:

```bash
git status --short
git add <specific files — never blanket>
git commit -m "<concise message>"
git push origin main        # primary (CHERP-Backup remote)
git push pipe-r main        # secondary (Pipe-R remote)
```

Skip `push pipe-r` if that remote is intentionally legacy for the current
change. Never force-push. Never skip hooks.

If there's nothing to commit, say so and move on.

## 4. Commit + push the CHERP workspace clone (if present)

If `workspace/CHERP` exists and is a git repo, repeat step 3 from that
directory:

```bash
cd workspace/CHERP
git status --short
git add <specific files>
git commit -m "<message>"
git push origin <current-branch>    # usually dev, sometimes main
```

Check the current branch first — phase-in-flight work goes to `dev`, only
merge to `main` when Ken says so (main auto-deploys to cherp.live).

## 5. Report the save summary

End with a tight summary:
- What files changed (grouped by repo)
- What commits landed (SHA + subject)
- What was pushed where
- What memory was added/updated
- What's queued for the next session (the immediate next step)

Keep it under 200 words. Ken should be able to close the session cleanly
after reading it.

## Guardrails

- NEVER commit `.env`, credentials, tokens, or `agent_mode/config/*.json`
  files that contain secrets
- NEVER `git add .` or `git add -A` — always stage specific files by name
- NEVER amend an existing commit unless Ken explicitly asked
- NEVER force-push
- If a pre-commit hook fails, fix the issue and make a NEW commit, don't
  skip the hook
- If you hit permission errors on Windows system directories, you're in
  the wrong cwd — switch to the project root and retry
