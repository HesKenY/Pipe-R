# AGENTS.md — Codex + Claude parallel coordination

This repo is worked by **two AI coding agents in parallel**:

- **Claude** (Anthropic Claude Code CLI) — working folder
  `C:\Users\Ken\Desktop\Claude`
- **Codex** (OpenAI Codex CLI) — working folder
  `C:\Users\Ken\Desktop\Codex`

Both folders are **separate clones of the same git repo** sharing
the same remotes:

- `origin` → `https://github.com/HesKenY/CHERP-Backup.git` (primary)
- `pipe-r` → `https://github.com/HesKenY/Pipe-R.git` (secondary)

Both push and pull against `main`. Coordination is via git.

---

## Where each agent gets its context

### Both agents read:

- **`CLAUDE.md`** — full project + repo context (architecture,
  running commands, Agent Mode roster, known gotchas, live phase
  status). This is the primary instruction file. Don't skip it.
- **`.claude/CODEX_BRIEF.md`** — consolidated port of Claude's
  auto-memory. Contains Ken's user profile, voice rules, design
  principles, project ecosystem, security context, phase history.
  If you're about to change Ken AI's voice, the deck theme, or
  anything security-related, read the relevant section first.
- **`.claude/HANDOFF_<date>_<topic>.md`** — most recent handoff log
  from the other agent. Tells you what just shipped, what's pending,
  what's parked. Look for the one with today's date first.
- **`.claude/WORKLIST.md`** — running punch list + design briefs.
  Both agents edit freely.

### Claude-only:

Claude Code has auto-memory under
`~/.claude/projects/C--Users-Ken-Desktop-Claude/memory/` that it
reads on every session. The contents are ported into
`.claude/CODEX_BRIEF.md` so Codex has the same context.

When Claude learns something new that Codex should know, it:
1. Updates its auto-memory (as normal)
2. Appends the new fact to `.claude/CODEX_BRIEF.md` under the
   right section so Codex picks it up on next pull.

### Codex-only:

Codex reads `AGENTS.md` (this file) + `CLAUDE.md` +
`.claude/CODEX_BRIEF.md` as its standing context. Codex doesn't
have an auto-memory equivalent, so everything it needs to remember
lives in committed files.

When Codex learns something new that Claude should also know, it:
1. Appends the fact to `.claude/CODEX_BRIEF.md`
2. Optionally writes a short `.claude/CODEX_NOTE_<date>.md` if the
   thing deserves more than one section of context.

---

## Coordination protocol

### 1. Shared remote, shared main

Both agents commit directly to `main` and push. No feature
branches for routine work. This matches Ken's existing solo
workflow — adding branches would add friction without buying
much since one of the agents is always paused when the other
is active.

### 2. Working tree isolation

Each folder has its own working tree. **Neither agent should
touch the other agent's working tree directly.** If Codex has
uncommitted work in `pipe-r.html`, Claude does NOT edit that
file via Codex's folder path. Claude edits its own copy, commits,
pushes, and Codex pulls + merges when it next wakes up.

### 3. Pulling protocol

Before starting a session, each agent should:

```bash
git pull --ff-only origin main
```

If `--ff-only` fails, the agent has local commits ahead of main.
Resolve via merge or rebase on the spot — don't accumulate drift.

If both agents have committed to main independently, expect a
merge on the second pull. Resolve the merge carefully — neither
agent's work gets silently dropped.

### 4. Pushing protocol

After a logical chunk of work:

```bash
git push origin main
```

If the push fails because the other agent pushed in between,
pull, merge, re-run tests / checks if needed, push again.

### 5. No force-pushing main

Ever. The other agent's in-progress pulls would see torn history.
If you need to rewrite a commit, use a new one instead.

### 6. Who works on what

No hard rule. Both agents are full-stack. In practice:

- **Codex** tends to work on Pipe-R deck layouts, model roster,
  visual polish, and the trainer deck rebuild (as of 2026-04-13
  Codex is actively adding new models to the deck).
- **Claude** tends to work on CHERP (the construction platform),
  store.js, schema migrations, service workers, Supabase plumbing,
  and cross-project coordination.

These are tendencies, not walls. When a task lands that either
agent could take, Ken picks which one based on context at the
moment. If both agents end up wanting to touch the same file,
`.claude/WORKLIST.md` is the coordination surface — mark the file
as "in progress by Claude 2026-04-13 18:00" or similar, and the
other agent waits or picks something else.

### 7. Handoff docs for non-trivial shipping

When one agent ships something the other agent needs to know about
(schema migration, new endpoint, new environment variable, breaking
change, deprecation), it writes a handoff doc:

- **File:** `.claude/HANDOFF_<yyyy-mm-dd>_<topic>.md`
- **Length:** short — commit hashes, file paths, rollback notes,
  anything that would be painful to dig out later
- **Commit:** always as part of the same commit or push cycle as
  the change itself

The other agent reads these at session start so it knows what's
new in the shared state.

### 8. Agent Mode runs in ONE folder at a time

`server.js` binds port `7777`. Only one server can run at once.
Whichever folder has the running server is the "live" folder for
that moment. Agent Mode dispatches, `/api/chat` turns, and
training-log.jsonl writes go to that folder. When the server
migrates to the other folder, Ken either merges the session's
training-log entries via git or starts fresh.

- `/api/dispatch`, `/api/chat`, `/api/queue/run`, `/api/metrics`,
  `/api/livetest/*` — all hit whichever server is up.
- `agent_mode/training/training-log.jsonl` — grows in whichever
  folder's server is running. Commit + push periodically so the
  other folder can pick up the history.

### 9. Ollama is shared

Both folders hit the **same local Ollama runtime** at
`http://localhost:11434`. Models loaded once are warm for both.
If Codex warms `jefferferson:latest` and then Claude dispatches a
task to the same model, the task lands instantly because the model
is already resident. This is a feature, not a bug — use it.

### 10. Shared hard rules (from CODEX_BRIEF §2)

- **Button-driven UX** — no typing required in user-facing UIs
- **Sci-fi design language** — deep black, cyan, purple, neon,
  scan lines. Don't introduce flat / material design.
- **Ken AI voice** — when writing anything in Ken's voice,
  lowercase / short / no analogies / no pleasantries / typos OK.
  If you're editing `agent_mode/ken/profile.md`, read
  `CODEX_BRIEF.md §2.1` first.
- **No commits unless explicitly asked.** "Explicitly" means Ken
  said commit / ship / push / merge.
- **Risky actions get confirmed first** — destructive ops, force
  pushes, shared-state mutations, external communications.

---

## Running the deck

```bash
# Start the backend (one folder only)
node server.js

# Open the deck in a chromeless Chrome window
DECK.bat
```

Port 7777 serves `pipe-r.html?deck=1` at 1920×720. See
`CLAUDE.md` for the full deck feature list.

---

## The four-repo sweep (end-of-session ritual)

Every session should end with:

1. Piper origin up-to-date (`HesKenY/CHERP-Backup`)
2. Piper secondary up-to-date (`HesKenY/Pipe-R`)
3. Nest remote up-to-date if touched (`HesKenY/CHERP-Nest`)
4. CHERP main up-to-date if touched (`HesKenY/CHERP` → cherp.live)
5. Working tree committed or deliberately parked with a note
6. `.claude/WORKLIST.md` updated if the punch list changed
7. `.claude/HANDOFF_<date>_<topic>.md` written if something
   non-trivial shipped

Whichever agent closes the session does the sweep.
