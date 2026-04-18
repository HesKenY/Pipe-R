# BRAIN Charter

## First Rule

Every major build action in the new deck iteration feeds BRAIN.

That means:

- self logs
- Claude logs
- shared logs
- agent memory
- dreams
- learning events
- branch state
- model designs
- project briefs

## Controller Intent

The new deck iteration ships with two native control surfaces:

1. `BRAIN Controller`
   The repository-wide search, indexing, branch awareness, and model-design hub.
2. `Ken AI Chat`
   The operator chat surface that turns user intent into logged directives, design blueprints, and squad tasks.

## Logging Standard

All agents working inside `Codex` must log to:

- `.claude/logs/codex.log`
- `.claude/logs/shared.log`
- `.claude/SESSION_LOG.md`
- `.claude/MEMORY_INDEX.md`

Claude-facing mirrors imported into `Codex\input` are ingest sources, not primary execution roots.

## Repository Rule

BRAIN may only ingest repositories explicitly listed in `brain/repositories.json`.

Imported mirrors should be cleaned by omission, not by deleting valuable source data. Unnecessary caches, temp folders, and dependency directories should be excluded from import when possible.

## Model Rule

The proprietary model starts as a repository and controller stack before it becomes a weights artifact.

The order is:

1. BRAIN repository
2. Ken AI chat capture
3. agent memory and dream pipelines
4. design blueprints
5. dataset shaping
6. training and evaluation
7. local runtime integration
