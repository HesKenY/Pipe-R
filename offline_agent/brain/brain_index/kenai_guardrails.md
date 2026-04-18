# kenai:v3 guardrails

Failure mode and discipline for every agent (Claude, Codex CLI, planner)
that calls kenai:v3 for direction.

## The failure mode

kenai:v3 has Ken's voice and reasoning patterns baked into its SYSTEM
block + ~30 MESSAGE priming pairs. It will sound CONFIDENTLY Ken-like
even on questions where Ken has not actually expressed a preference.

Trusting kenai:v3's "first opinion" without verification will produce
real-Ken-flavored fake-Ken-judgments. Worst case: a plausible-sounding
answer leads us into a decision Ken would never have made.

## The three-tier output contract

Every kenai:v3 response is shaped as one of:

| Tier | Label | Shape | Treatment |
|------|-------|-------|-----------|
| 1 | confident | terse imperative — "no. just change the code." | Use directly. Verify against code/state for high-stakes. |
| 2 | uncertain | hedge prefix + best guess + flag — "not sure. probably postgres. ask if it matters." | Use as starting point. Surface the uncertainty in your own next response to Ken. |
| 3 | defer | "no rule. ask ken." | Stop. Surface to Ken. Don't act. |

Hedge phrases that put a response in tier 2:
- "not sure. but i'd guess [X]."
- "no rule. probably [X]. ask if it matters."
- "guessing here — [X]. flag if wrong."

Hedge phrases that put a response in tier 3:
- "no rule. ask ken."
- "no rule for this. high stakes. ask ken before deciding."

The Modelfile's SYSTEM block teaches kenai:v3 to emit this shape.
The wrapper `Codex/brain/ask_kenai.py` parses the prefix and tags
every response with its tier.

## Discipline for callers

1. **Always go through `ask_kenai.py`**, never raw `ollama run kenai:v3`.
   The audit log at `Codex/brain/snapshots/kenai_audit.jsonl` is how
   we curate bad answers into next training corpus.

2. **Treat the tier as load-bearing**, not decorative:
   - tier 1 → use directly for low/medium stakes; verify on high stakes
   - tier 2 → starting point only; surface the uncertainty to Ken in
     your own next message
   - tier 3 → stop. Ask Ken.

3. **High-stakes operations always require Ken**, regardless of tier:
   - file/directory deletes
   - production deploys
   - schema migrations
   - destructive git operations
   - changes to money/pricing/customer-facing copy
   - novel architecture decisions

4. **Write back what kenai said + how you used it.**
   When you act on a kenai response, log: `{question, kenai_answer,
   tier, your_action, outcome}` so we can curate retroactively.

5. **Disagreements override training.** If Ken in the current
   conversation says X and kenai:v3 says Y, defer to current Ken.
   Then add a MESSAGE pair to the next Modelfile so kenai learns.

## Cross-check pattern (medium+ stakes)

For decisions where wrong is expensive but not catastrophic:

1. Ask kenai cold: "should we X?"
2. Ask kenai with grounding: "what specific rule from your training
   supports answering 'should we X' the way you did?"
3. If pass-2 can't cite a rule, treat pass-1 as a guess (effectively
   tier 2 even if it tagged itself tier 1).

## Kill switch

`Codex/offline_agent/config/.kill_switch` exists as a file → all
tool execution halts. The UI button in offline_agent does the same.
Verify it works before any autonomous loop.

## Audit + retrospective curation

- All queries: `Codex/brain/snapshots/kenai_audit.jsonl`
- Bad answers Ken thumbs-down become "refuse" examples in next v3.X
- Drift detection: if kenai's tier-1 answers start failing in
  practice, lower the trust ceiling for that domain
