# Pipe-R Rebuild — Codex Integration Plan

**Status:** Monitoring only. Do NOT execute without Ken's greenlight.
**Last scanned:** 2026-04-12 — Codex workspace files dated Apr 12 10:38–11:41

---

## What Codex delivered (per `workspace/CHANGES.md`)

### Completed goals
- **Goal 1 — retry cap + backoff** (✅ claimed)
  Files: `agent_mode/core/queue.js`, `agent_mode/core/executor.js`, `agent_mode/core/orchestrator.js`, `agent_mode/config/runtime.json`
  Adds retry caps, retry timestamps, exponential backoff, dead-letter handling for agent tasks.

- **Goal 2 — agent health routing** (✅ claimed)
  Files: `agent_mode/core/registry.js`, `agent_mode/core/orchestrator.js`, `agent_mode/config/agents.json`, `agent_mode/ken/profile.md`, `hub.js`, `server.js`
  Unhealthy-agent routing, manual heal controls, marks `jefferferson:latest` as unhealthy.

- **Goal 3 — missing web UIs** (✅ claimed)
  Files: `pipe-r.html` (68 KB), `remote.html` (28 KB), `server.js` (/api/dashboard), `agent_mode/config/runtime.json`
  P0K3M0N-style-on-Game-Boy-Advance themed trainer workbench + PIN-gated (1996) phone remote.

- **Goal 5 — Ollama health-check UI in hub** (✅ claimed)
  Files: `hub.js` (rebuilt Agent Mode section)

### Skipped goals
- **Goal 4 — modularize `hub.js`** — not started. Still one file.
- **Goal 6 — CHERP mycrew.js auto-refresh** — not started.
- **Goal 7 — Nest dependency install hook** — not started.

### Creative additions (unprompted, flag for Ken's approval)
- **"P0K3M0N trainer party" theme.** Codex reframed the 7 agent slots as a Pokemon trainer (Ken AI) + 6 party specialists + 1 companion learning slot (`m3w-learning:latest`, Slot 8). Display names now use leetspeak:

  | Slot | Base model | New display name | Role |
  |---|---|---|---|
  | 0 (trainer) | `ken-ai:latest` | Ken AI (trainer) | Trainer Orchestrator |
  | 1 | `qwen2.5-coder:14b` | 5c1z0r Patchsmith | Implementation Engineer |
  | 2 | `forgeagent:latest` | R0t0m Relay | Integration Engineer |
  | 3 | `cherp-piper:latest` | D3c1du3y3 Pathfinder | Product Scout |
  | 4 | `llama3.1:8b` | P0ryg0n Logdex | Observability Analyst |
  | 5 | `jefferyjefferferson:latest` | Umbr30n Safeguard | QA Engineer |
  | 6 | `jefferferson:latest` | 4l4k4z4m Archive | Memory Engineer (unhealthy) |
  | 8 (companion) | `m3w-learning:latest` | M3w Promptdex | Learning Agent (pending build) |

- **Charter files.** Each specialist got a markdown doctrine file under `agent_mode/training/charters/*.md`.
- **Preferred partners + handoff contracts.** Each agent has a `preferredPartnerId`, `preferredPartnerReason`, `teamMission`, `handoffContract`. This is actually a solid data model for duo routing regardless of the Pokemon theme.
- **Leetspeak rename pass.** Codex explicitly called out a "leet alias pass" to make names "feel more stylized than literal." This conflicts with the rebuild brief's "no renames" rule if interpreted strictly.

---

## Merge risk assessment

### HIGH risk — real conflicts with tonight's work

1. **`agent_mode/core/queue.js`** — both Codex and I edited it.
   - Codex: added retry caps, backoff, dead-letter
   - Me: fixed `add()` to honor `opts.assignedAgent` (Pipe-R commit `02d0d6f`)
   - **Resolution:** merge both — my one-line fix must survive Codex's larger rewrite.

2. **`agent_mode/core/executor.js`** — both touched.
   - Codex: retry loop integration, trainer/party metadata in prompts
   - Me: switched `execSync` → `spawnSync` with stdin piping (commit `02d0d6f`)
   - **Resolution:** CRITICAL — my spawnSync fix is what makes the model outputs correct. If Codex still has `execSync` with the prompt as a quoted arg, every agent will go back to producing garbage. Must verify Codex preserved stdin piping or re-apply it.

3. **`agent_mode/core/orchestrator.js`** — both touched.
   - Codex: retry cap + backoff + dead-letter dispatch
   - Me: fixed `createTask()` to pass `assignedAgent` through (commit `02d0d6f`)
   - **Resolution:** merge both.

4. **`agent_mode/config/agents.json`** — both touched.
   - Codex: rewrote with party slot structure, charter files, leetspeak names, added M3w slot
   - Me: flipped `ken-ai:latest` from `pending_build` to `idle`, added `builtAt: 2026-04-12T06:05:00Z`
   - **Resolution:** start from Codex's version (richer data model), patch in my ken-ai status flip. Strip leetspeak names only if Ken rejects the theme.

5. **`agent_mode/ken/profile.md`** — both edited.
   - Codex: based on ORIGINAL v1 (still contains line 44 "Construction analogies when explaining abstract concepts"). Added a "Trainer Party Model" section at the bottom describing the 7-specialist doctrine.
   - Me: rewrote tonight to drop plumber analogies and match Ken's actual typed voice (commit `d1a7bb8`). Added lowercase rule, typos-OK rule, concrete examples.
   - **Resolution:** CRITICAL. Start from my version (tonight's voice rewrite). Bring in Codex's "Trainer Party Model" section verbatim at the bottom — it's additive and valuable. Do NOT re-introduce the analogy instruction.

6. **`agent_mode/ken/Modelfile`** — I rewrote the SYSTEM block tonight to match the new voice. Codex didn't touch it. **Resolution:** keep my version, just rebuild the model after the merge.

7. **`hub.js`** — Codex rewrote the Agent Mode section. ~205 KB. My changes to `hub.js` during the current live session: none. **Resolution:** can probably accept Codex's hub.js wholesale, but diff against current to confirm nothing else was touched.

### MEDIUM risk

- **`server.js`** — Codex added `/api/dashboard`, remote PIN checks, dispatch gates. I haven't edited server.js this session. **Resolution:** likely safe to take Codex's version. Verify `/api/dispatch` still respects `agent` field.
- **`agent_mode/config/runtime.json`** — Codex added theme/routing/PIN fields. My version has `mode, autoExecute, autoExecuteInterval, requireClaudeReview, maxConcurrentTasks, maxRetries`. **Resolution:** merge — take Codex additions, keep my fields if they're not in Codex's version.

### LOW risk — purely additive, safe to copy

- **`pipe-r.html`** — new file, didn't exist in live repo. Safe.
- **`remote.html`** — new file, didn't exist in live repo. Safe.
- **`agent_mode/training/charters/*.md`** — new charter files. Safe.
- **`agent_mode/training/README.md`** — new file. Safe.

---

## Open questions for Ken

1. **Theme approval.** Do you want the "P0K3M0N trainer party" framing to ship, or should Codex strip the leetspeak names and keep the data model (partner preferences, charter files, handoff contracts) under generic role names? The underlying data structure is good regardless — it's just the display layer.

2. **M3w Promptdex (slot 8).** Codex added a new learning agent slot backed by a model that doesn't exist yet (`m3w-learning:latest`). Ship as `pending_build` and decide later, or cut it from the merge?

3. **Voice reconciliation.** Your voice rewrite from tonight (lowercase, no analogies, concrete examples) lives in `C:\Users\Ken\Desktop\Claude\agent_mode\ken\profile.md`. Codex's version is based on the older v1 with plumber analogies still in. Confirming: keep tonight's voice, add Codex's "Trainer Party Model" section underneath. Yes/no?

4. **Remote PIN = 1996.** Codex set the remote.html PIN to `1996` as a placeholder. Change it before merging?

5. **`/api/dispatch` regression check.** After merge, I need to re-verify that dispatching with `agent: "ken-ai:latest"` still routes correctly and the spawnSync stdin path is intact. Can I do a single smoke-test dispatch after the merge before declaring done?

---

## Proposed merge procedure (when you give the go)

1. **Pre-merge snapshot.** Tag current Pipe-R state (`git tag pre-codex-merge` locally) so we can roll back if needed.
2. **Work on a branch.** `git checkout -b codex-merge` in the live repo.
3. **Additive files first (low risk).** Copy `pipe-r.html`, `remote.html`, `agent_mode/training/` wholesale from the Codex workspace.
4. **Structural conflicts.** For each of queue.js / executor.js / orchestrator.js / agents.json / profile.md / Modelfile / runtime.json: take Codex's version as the base, then patch in my tonight's changes that are missing (list them above, file by file).
5. **hub.js / server.js.** Diff current live vs Codex. If current live has no edits from tonight (it doesn't, I checked), accept Codex's versions wholesale.
6. **Voice sanity check.** Run one smoke-test dispatch against ken-ai after rebuild. Expected: no plumbing analogies, lowercase voice, direct answer. If it regresses, revert the profile.md merge.
7. **Orchestrator sanity check.** Dispatch a task to each of the 7 agents. Look for: real assignment respect (no silent auto-reroute), real model outputs (no shell-escaped prompt garbage), no retry storms on failures.
8. **Commit + merge to main.** Squash-merge the branch with a single commit referencing the Codex rebuild folder.
9. **Remove `Pipe-R Rebuild (Codex)` folder?** Ask Ken. My vote: archive, don't delete. Move to `.claude/archive/` in case we need to reference the original handoff files later.

---

## What I'm doing right now

Nothing to the Codex folder. Nothing to the live Pipe-R repo. Just this plan file + any new monitor runs you ask for.

When you say "go", I start with step 1 of the merge procedure above and report after each phase.
