# Session 2026-04-16/17 — kenai:v3 build + autonomous Pokemon launch

One long session that shipped the v3 corpus, built the model, wired it up,
exposed + patched multiple bugs, built a fast variant, and got autonomous
Pokemon Crystal play running at sub-second inference with rule enforcement.

## What shipped

### v3 corpus + model
- **v3 corpus merged** — 190 rows at `offline_agent/brain/training/modelfiles/2026-04-17T01-22-03-kenai-v3.unsloth.jsonl`. Sources: v2 baseline (49) + Modelfile MESSAGE pairs (19) + Pokemon Crystal (88) + CHERP code-dev (17) + Ken voice (17). Zero dedupe collisions.
- **Build script** at `brain/build_v3_corpus.py` — re-runnable merger. Reads `corpora/{pokecrystal,cherp,ken_voice}/` + Modelfile MESSAGE pairs + v2 baseline, dedupes by hash, emits alpaca JSONL + manifest.
- **Canonical corpora** moved to `C:/Users/Ken/Desktop/Codex/corpora/pokecrystal/` per Ken's org rule ("codex = folder, brain = memory/archive/logs, corpora live at codex top-level").
- **kenai:v3 Modelfile** at `offline_agent/brain/training/modelfiles/kenai-v3.Modelfile` — FROM ken-ai:latest + Pokemon Crystal rules + CHERP gotchas + three-tier uncertainty framing + Halo (v1 carryover). 299 lines, num_ctx 32768.
- **`ollama create kenai:v3`** — built. 9.0GB. Verified via `ask_kenai.py` with three tier-classification test cases (tier 1 confident, tier 2 uncertain, tier 3 defer) — all fired correctly.

### Guardrails (the failure mode I flagged at Ken's prompt: "kenai:v3 will sound confidently Ken-like even when wrong")

- **Three-tier uncertainty framing baked into v3 SYSTEM block.** tier 1 = confident imperative; tier 2 = "not sure. i'd guess X. ask if it matters."; tier 3 = "no rule. ask ken."
- **Priming pairs added** — 8 pairs teaching the model to emit tier 2/3 answers on novel / high-stakes questions instead of confabulating.
- **`Codex/brain/ask_kenai.py`** — wrapper that parses response prefix to classify tier, logs every (question, answer, tier) to `brain/snapshots/kenai_audit.jsonl` for retrospective curation.
- **Guardrails doc** at `offline_agent/brain/brain_index/kenai_guardrails.md` — discipline for all agents (Claude, Codex CLI, planner): always go through ask_kenai.py; treat tier as load-bearing; high-stakes always goes to Ken regardless of tier.
- **Self-rule memory** saved at `~/.claude/projects/C--Users-Ken-Desktop-Claude/memory/feedback_kenai_v3_routing.md` — Claude's discipline for routing tier-1/2/3 responses.

### Rules I set and put in auto-memory this session

- **codex** = `C:\Users\Ken\Desktop\Codex` (the folder, not the CLI)
- **brain** = memory/archive/logs inside codex. Document everything into brain.
- Default new work to codex. Claude folder is stale/parallel state.
- Before deleting/condensing anything in codex, snapshot to brain first.

### Offline agent + Pokemon wiring

- **`offline_agent/config/models.yaml`** — planner profile updated: `kenai:v1` → `kenai:v3`. Fallback chain: kenai:v2 → kenai:v1 → ken-ai → qwen → llama3.1.
- **Pokemon agent.js** — `_model = 'kenai:v3'` initially. Later switched to `kenai-fast`.
- **KENAI_v3.bat** launcher created.

### Bugs found + fixes shipped

1. **Planner SYSTEM override bug.** `offline_agent/agent_core/planner.py` built its own `SYSTEM_PROMPT` and passed to `client.chat(messages, system=...)`, which **overrides** the Modelfile's SYSTEM block entirely. Voice rules never reached the model. **Fix:** merged voice rules + three-tier framing into planner's SYSTEM_PROMPT so they survive the ollama API override. Requires offline_agent restart to pick up.

2. **agent.js prompt conflicts with Modelfile rules.** Hardcoded `activity=dialogue → press a` in buildPrompt() rules. Baked v3 rule is B (avoids NPC re-trigger). **Fix:** rewrote rules block: dialogue → B, battle → A, exploring → directional, + "after dialogue ends walk a tile before pressing A" cooldown.

3. **Code-level force-B enforcement.** 8B kenai-fast didn't internalize dialogue→B as tightly as 14B v3 did. **Fix:** added rule-enforcement layer in `tick()` — if activity=dialogue and action=a, force to b. Verified working: model emitted "press a", code wrote "b" multiple times in a row. Model eventually started emitting "b. advance dialogue." voluntarily.

4. **spawnSync blocks event loop.** `refreshVision()` used spawnSync with 50s timeout, blocking the entire Node HTTP server for 20-40s per vision call. **Fix:** refactored to async `spawn` with stdout chunking + close/error callbacks + kill-timeout.

5. **VRAM pressure — vision evicting kenai.** llama3.2-vision (7.8GB) + kenai-fast (4.9GB) thrashed VRAM, causing 30s stalls when kenai got evicted and had to cold-reload. **Fix (Option 3):** gated vision refresh by activity — only runs every tick (15s) when `lastActivity=battle`; every 4th tick (60s) otherwise. Overworld walking no longer thrashes VRAM.

6. **Activity classifier is motion-only and misfires.** `pokemon_tick.py` `classify()` returns "dialogue" for any motion 0.005-0.03 when OCR is empty. **Partial fix:** agent.js now overrides `state.activity` with `_visionCache.situation` when vision has a confident classification. Motion fallback only when vision absent.

7. **Pokemon corpora wrong location.** Initial work landed in `Claude/agent_mode/pokecrystal/` instead of codex. **Fix:** snapshotted to `Codex/brain/snapshots/2026-04-16T_pre_v3_merge/`, moved canonical copies to `Codex/corpora/pokecrystal/`, deleted Claude-side dupes. Compile script updated to read from codex path.

### kenai-fast variant (speed win)

- **`offline_agent/brain/training/modelfiles/kenai-fast.Modelfile`** — FROM `llama3.1:8b`, num_ctx 8192. Same SYSTEM block + priming pairs as v3 (model-agnostic text).
- **Built** via `ollama create kenai-fast`. 4.9GB.
- **Inference:** 30s cold → 13s second call → **sub-second warm** (measured 635-830ms repeatedly).
- **Quality trade:** 8B less tightly follows voice rules — emits prose like "press a. main menu. need to start or continue a game." The action parser handles the prose fine, and code enforcement catches rule violations.

### Monitor armed on pokemon-log.jsonl

- Tailing `Codex/agent_mode/memories/ken-ai-latest/pokemon-log.jsonl` filtering for state transitions + battle reviews + post-mortems + errors. Idle spam suppressed.

## Current state (end-of-session)

- Pipe-R server running at :7777
- Pokemon loop running on kenai-fast at tickMs=700
- Vision gated — only runs in battle or every 60s fallback
- Rule enforcement active (force-B on dialogue if model says A)
- Anti-stuck active (cycles directions if model repeats A+b+noop with low motion)
- Inference hitting sub-second when warm; occasional 8-15s when vision loads
- Monitor pinging Claude on meaningful state changes

## Open items

- **Real LoRA fine-tune of v3.** The `*.unsloth.jsonl` is prepped but not trained. Needs unsloth/axolotl run with GPU.
- **Classifier OCR empty.** pytesseract not reading GBC font reliably. Workaround: vision override. Real fix: train GBC-font-specific OCR or switch to vision-as-primary classifier.
- **offline_agent tool verification.** Planner system prompt is fixed, but tool surface (read_file, write_file, run_command, patch_apply) isn't smoke-tested end-to-end. Phase 3-4 of the build plan.
- **Phone access (path 2).** PipeR-Remote-Android exists + Tailscale is up. Need a minimal kenai-chat page on the deck. Ken said go when ready.
- **Pokemon voice tightening.** If we want kenai-fast to emit "b" directly instead of needing the code override, add more dialogue→b MESSAGE pairs to the Modelfile and rebuild.

## Files touched

New:
- `Codex/brain/build_v3_corpus.py`
- `Codex/brain/ask_kenai.py`
- `Codex/brain/snapshots/kenai_audit.jsonl` (append-only)
- `Codex/brain/snapshots/2026-04-16T_pre_v3_merge/` (pre-cleanup archive)
- `Codex/brain/snapshots/2026-04-17_kenai_v3_pokemon_autonomous.md` (this file — should move to brain/sessions/)
- `Codex/brain/sessions/2026-04-17_kenai_v3_pokemon_autonomous.md` (this file)
- `Codex/brain/exports/2026-04-17T01-22-03-kenai-v3.manifest.json`
- `Codex/corpora/pokecrystal/{type_chart,gym_leaders,starters}.json`
- `Codex/corpora/pokecrystal/strategy.md`
- `Codex/corpora/cherp/code_dev.json`
- `Codex/corpora/ken_voice/voice.json`
- `Codex/offline_agent/brain/training/modelfiles/kenai-v3.Modelfile`
- `Codex/offline_agent/brain/training/modelfiles/kenai-fast.Modelfile`
- `Codex/offline_agent/brain/training/modelfiles/2026-04-17T*-kenai-v3.Modelfile`
- `Codex/offline_agent/brain/training/modelfiles/2026-04-17T01-22-03-kenai-v3.unsloth.jsonl`
- `Codex/offline_agent/brain/brain_index/kenai_guardrails.md`
- `Codex/KENAI_v3.bat`

Modified:
- `Codex/offline_agent/agent_core/planner.py` (SYSTEM_PROMPT rewrite with voice + tiers + codex/brain defs)
- `Codex/offline_agent/config/models.yaml` (planner → kenai:v3, fallback chain)
- `Codex/agent_mode/pokemon/agent.js` (model=kenai:v3→kenai-fast; vision classifier override; force-B on dialogue; async refreshVision; vision gating; prompt rules rewrite; ADAPT rule)

Deleted (snapshotted to brain first):
- `Claude/agent_mode/pokecrystal/` (whole folder)
- `Claude/agent_mode/training/poke-corpus.jsonl`
- `Claude/.claude/logs/pokeapi-fetch.log`

## Metrics

- Corpus size: 190 rows, up from ~49 in v2
- Inference speed: 27s (v3 cold) → 0.6-0.8s (kenai-fast warm)
- Rule enforcement firings this session: force-B on dialogue: ~5+ confirmed
- Anti-stuck firings: multiple (direction cycling when model repeated A)
- kenai:v3 guardrail audit entries: 5 (3 smoke tests + 2 domain tests)


## Running timeline — autonomous play session

Times UTC. Each entry is a code-layer observation about the agent's behavior.

### Timeline

- **02:23:46** — First non-idle tick. activity=exploring, motion=0.56. Agent woke up after mGBA came into focus.
- **02:25:51** — First dialogue tick with OLD rules. Model pressed 'a' per agent.js prompt bug (should be 'b' per v3 baked rule).
- **~02:27-28** — Ken killed + restarted Pipe-R, then pokemon loop restarted on kenai:v3 with patched agent.js rules.
- **02:30:52** — Dialogue tick, kenai:v3 chose 'start' not 'b'. Baked rule not propagating — prompt rules override baked knowledge.
- **~02:33** — Switched pokemon loop to kenai-fast (llama3.1:8b base). Cold-start 30s → warm 13s → sub-second.
- **02:35:21** — First sub-second inference: **823ms**. kenai-fast warm.
- **02:35:35** — Force-B rule implemented. Dialogue activity + model said 'press a' → code forced to 'b'. ENFORCEMENT WORKING.
- **02:39:03** — 30s stall: kenai-fast got evicted from VRAM (llama3.2-vision load event). raw='', action=noop.
- **~02:40** — Patched Option 3: vision refresh gated by activity. Only runs when battle OR every 60s. Stops VRAM thrash on overworld.
- **02:42:07** — kenai-fast voluntarily emitted **'b. advance dialogue.'** — in-context learning visible. Rule internalized after repeated force-B corrections.
- **02:44:33** — Sustained clean b-for-dialogue: terse Ken-voice output ('b. advance dialogue.', 659ms).
- **02:44:47** — Force-B fires again on a different tick (model drifts back to 'a'). Code enforcement keeps output correct.

### Rule enforcement fire count (monitor-observed, this session)

- **force-B on dialogue:** 5+ observed (model said 'a' / 'press a', code wrote 'b')
- **anti-stuck direction cycle:** 2+ observed (low motion + repeated a → down/right)
- **voluntary b-emission:** 2 observed (model learned the rule)

### Sub-second inference count (this session)

Approx 8 sub-second ticks (623-931ms) once kenai-fast warmed. VRAM-evict stalls (30s) are rare now that vision is gated.

### Outstanding concerns

- activity=dialogue vs activity=exploring flip-flopping rapidly. motion thresholds are fooling the classifier. Vision classifier override only helps when vision cache is populated (which gated vision reduces).
- Consider: force classifier sanity check — if motion > 0.05 for 3+ ticks, prefer 'exploring' regardless of OCR/motion absolute value.

