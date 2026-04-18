---
name: How to use kenai:v3 — three-tier routing rule
description: When asking kenai:v3 for direction, parse the tier and route accordingly. Never trust tier-1 blindly on high stakes.
type: feedback
originSessionId: 4f2069d0-f62b-4932-beb3-48c801257e56
---
kenai:v3 (Ken's offline Claude Code model, born 2026-04-17) emits one of
three confidence tiers in every answer. Treat them as load-bearing:

**Tier 1 — confident** (terse imperative): "no. just change the code."
- Use directly for low/medium stakes
- Verify against code/state for high stakes (deletes, deploys, schema)

**Tier 2 — uncertain** (hedge prefix): "not sure. probably postgres."
- Use as a starting point only
- Always surface the uncertainty in my next message to Ken
- Don't pretend it was a confident answer

**Tier 3 — defer** ("no rule. ask ken"):
- Stop
- Surface to Ken before doing anything
- Don't act on the implied guess

**Why:**
kenai:v3 has Ken's voice baked in. It will sound confidently Ken-like
even on questions where Ken hasn't expressed a preference. Trusting
tier-1 blindly produces fake-Ken decisions.

**How to apply:**
- Always go through `Codex/brain/ask_kenai.py`, never raw `ollama run`.
  The wrapper tags every response with its tier and logs to
  `Codex/brain/snapshots/kenai_audit.jsonl` for retroactive curation.
- For high-stakes operations (file deletes, production deploys, schema
  migrations, destructive git ops, money/pricing/customer-facing
  changes, novel architecture), ALWAYS go to Ken regardless of tier.
- For medium+ stakes, use the cross-check pattern: ask kenai twice —
  once cold, once with "what rule supports your answer?" — if pass-2
  can't cite a rule, treat pass-1 as tier 2.
- When kenai disagrees with current-conversation Ken, defer to Ken.
  Then suggest adding a MESSAGE pair to next Modelfile.
- Full guardrail discipline lives at
  `Codex/offline_agent/brain/brain_index/kenai_guardrails.md`.
