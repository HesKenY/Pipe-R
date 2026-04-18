---
name: Ken AI — built v1 (personality scaffold)
description: Ken's personality AI is built and registered. v2 (real fine-tune) blocked on training data volume.
type: project
originSessionId: 612ace6e-1cd4-4973-a8c2-48e2d51c1a07
---
**v1 — BUILT 2026-04-12.** `ollama create ken-ai -f agent_mode/ken/Modelfile`
ran cleanly. Model ID `326ad05d282a`, 9 GB, based on qwen2.5-coder:14b with
`agent_mode/ken/profile.md` as the SYSTEM prompt. Smoke-tested via
`ollama run` — responds, follows the profile voice. `agents.json` is flipped
from `status: pending_build` → `idle` with `builtAt: 2026-04-12T06:05:00Z`,
so the orchestrator can dispatch tasks to it on the next 30s tick.

**Why this version is "scaffold not fine-tune":** v1 is prompt-based
personality — the SYSTEM prompt carries all of Ken's voice, rules, and
hard-no's. No weights changed. Rebuilding is `ollama create` (seconds).
This was the right call to unblock day-to-day Ken-style work without
waiting for training data to accumulate.

**v2 — real fine-tune, blocked on data.** The long-term plan is a proper
LoRA/full fine-tune against `agent_mode/training/training-log.jsonl` once
there are enough curated, voice-matched entries to justify it. Curation
script (`curate.js`) is deferred until the data volume is there. Every
task Ken AI runs under the orchestrator adds to training-log.jsonl, so
v2 builds itself over time.

**How to apply:**
- Route personality-critical work (Ken-voice writeups, decision drafts,
  coding tasks that should "sound like Ken") to `ken-ai:latest`.
- To tune the voice, edit `agent_mode/ken/profile.md` and rerun
  `ollama create ken-ai -f agent_mode/ken/Modelfile` — the personality
  is in the file, not baked into the weights.
- Don't conflate v1 with a "true" fine-tune — if someone asks whether
  Ken AI was trained on Ken's data, the honest answer is "not yet".
