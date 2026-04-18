---
name: Definitions and rules — codex, brain, documentation
description: Load-bearing terminology rules between Ken and Claude. Codex = the folder. Brain = memory/archive/logs. Document everything into brain.
type: feedback
originSessionId: 4f2069d0-f62b-4932-beb3-48c801257e56
---
These are durable definitions Ken set 2026-04-16. Use them in every
future conversation unless Ken explicitly overrides for one task.

## Definitions

- **codex** = the folder `C:\Users\Ken\Desktop\Codex`. When Ken says
  "codex" he is referring to that directory specifically, not the
  OpenAI Codex CLI agent (which is also called Codex).
- **brain** = the memory / archive / log / index system inside codex.
  Specifically the top-level `Codex\brain\` folder PLUS the per-agent
  memory subsystem (`offline_agent\brain\`, `agent_mode\memories\*\`).
- "we document everything into brain" — every meaningful artifact,
  decision, log, snapshot, lesson, design, or removed-but-still-valuable
  content lands in brain. Brain is the master log.

## Rules that follow from these definitions

- **Why:** Ken needs one consistent vocabulary across sessions; both
  agents (Claude + the Codex CLI) need to speak the same way. Without
  this, "codex" gets ambiguous and brain-vs-memory-vs-logs creates
  organizational drift.
- **How to apply:**
  - Default workspace for new work is **codex**, not the Claude folder.
    The Claude folder is older parallel state and should NOT receive
    new feature scaffolding.
  - Before deleting / removing / condensing anything from any file in
    codex, FIRST ensure the removed content is captured in brain
    (snapshot, archive, or appropriate index file).
  - When proposing where to put a new artifact, default to a brain
    subfolder if it's documentation/log/archive in nature; default to
    a code path inside codex (`offline_agent/`, `agent_mode/`, etc.)
    if it's executable.
  - When Ken says "codex" or "brain" in a sentence, treat it as
    referring to these specific paths, not the abstract concepts.
  - Use my own auto-memory ("claude.md") for cross-session continuity
    — i.e., save persistent rules and project context here so I show
    up to the next session pre-loaded.
