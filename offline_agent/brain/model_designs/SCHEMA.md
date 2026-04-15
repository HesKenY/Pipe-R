# Model Design Schema

Every proprietary model build planned through this project
produces a design document that follows the schema below.

Anchored on `Codex/brain/MODEL_DESIGNER_SPEC.md`. The 9 required
outputs in that spec map to the fields here. Anything missing
is a hard block on dataset curation — `model_designer.py`
refuses to emit a training spec for a design with unfilled
required fields.

## File layout

```
brain/model_designs/
  <slug>/
    design.json         ← the machine-readable design (this schema)
    design.md           ← human-readable narrative
    notes/              ← design-session notes, diagrams, sketches
    revisions.jsonl     ← append-only log of every change to design.json
```

## design.json fields

```json
{
  "slug":             "<kebab-case-id>",
  "name":             "<short display name>",
  "version":          "0.1.0",
  "created":          "2026-04-14T14:00:00",
  "updated":          "2026-04-14T14:00:00",
  "operator":         "Ken",
  "source":           "offline_agent",

  "mission":          "<one paragraph, what this model is for>",

  "capabilities": [
    "local-first execution",
    "tool execution",
    "shell execution",
    "source control awareness",
    "visual perception",
    "project planning",
    "memory logging",
    "dream synthesis",
    "branch-aware reasoning",
    "UI control scaffolding"
  ],

  "permissions": {
    "profile":       "full-trust local mode",
    "modes_allowed": [0, 1, 2, 3],
    "kill_switch":   true,
    "audit":         true,
    "read":          ["approved project files", "logs", "metrics"],
    "write":         ["workspace/", "brain/", "logs/"],
    "execute":       ["local tools", "shell commands", "git"],
    "vision":        ["screenshot", "window capture"],
    "desktop":       ["mouse", "keyboard", "hotkeys"],
    "never":         ["C:/Windows/System32", "~/.ssh", ".env files"]
  },

  "memory_strategy": {
    "index_layout":   "brain_index/ + sessions/ + tasks/ + corpus/ + training/",
    "retrieval":      "sqlite fts5, baseline + top-k chunks per turn",
    "baseline":       ["identity.md", "rules.md"],
    "max_context_bytes": 12000,
    "session_rollup": "daily session_log.md, auto-append per turn",
    "task_tracking":  "tasks/open/ + tasks/done/ with fts indexing"
  },

  "dream_strategy": {
    "enabled":        true,
    "cadence":        "end of session + nightly",
    "inputs":         ["session logs", "training-log rows", "drill run outputs"],
    "outputs":        "brain/sessions/<date>/dream_<n>.md",
    "stamping":       "top insights get copied into brain_index/known_fixes.md"
  },

  "training_sources": [
    {
      "name":  "halo-trainer corpus",
      "path":  "brain/corpus/halo-trainer-*.jsonl",
      "kind":  "drill_passing_rows",
      "filter": "grade.passed == true"
    },
    {
      "name":  "pipe-r training log",
      "path":  "brain/training/training-log-recent.jsonl",
      "kind":  "dispatch_rows",
      "filter": "success == true AND approved == true"
    },
    {
      "name":  "session logs",
      "path":  "brain/sessions/**/session_log.md",
      "kind":  "narrative",
      "filter": "last 30 days"
    },
    {
      "name":  "brain_index",
      "path":  "brain/brain_index/*.md",
      "kind":  "reference",
      "filter": "always include"
    }
  ],

  "evaluation_goals": [
    "reason across indexed project memory",
    "use tool and shell workflows safely in local mode",
    "retain branch-aware and repo-aware context",
    "match Ken's voice on all non-code responses",
    "emit valid JSON for structured tool calls without fences"
  ],

  "runtime_plan": {
    "host":     "127.0.0.1:7778 (FastAPI + websocket)",
    "runtime":  "Ollama local",
    "base":     "ken-ai:latest (qwen2.5-coder:14b + profile.md)",
    "fallbacks": ["qwen2.5-coder:14b", "llama3.1:8b"],
    "deployment": "replace ken-ai:latest modelfile after first real fine-tune"
  },

  "rollout_risks": [
    "voice drift if training corpus has too many non-Ken-voice rows",
    "tool call format regression if structured-output training over-weighted",
    "context window saturation if brain imports grow too fast",
    "cascading failure if ollama fallback chain isn't tested per release",
    "permission escalation bypass if kill switch isn't checked on every tool call"
  ],

  "status": "draft|review|approved|training|evaluating|deployed|retired"
}
```

## Required fields (refuses to train without)

- slug, name, mission, capabilities, permissions, memory_strategy,
  training_sources, evaluation_goals, runtime_plan, rollout_risks

`dream_strategy` and `notes` are optional — a design without them
builds, just loses points on the evaluation_goals pass.
