# HANDOFF 2026-04-13 — Phase 9 complete + real stats engine + dreams/learning/parallel-Codex setup

**Who wrote this:** Claude Opus 4.6 (1M context), running out of
`C:\Users\Ken\Desktop\Claude`.

**Who this is for:** Codex, or a future Claude session starting in
either folder. Read alongside `CLAUDE.md` + `AGENTS.md` +
`.claude/CODEX_BRIEF.md`.

**Commit range on the Piper repo (`HesKenY/CHERP-Backup`):**
from `89b2834` (start of session) through whatever got pushed at
wrap time. See `git log --oneline` for the exact sequence.

---

## 1. CHERP main shipped today (commits in `HesKenY/CHERP`)

All already live on cherp.live via Netlify.

- **`bf53180`** — Phase 7a: employee-id DMs on pipe_messages
  (new columns `from_employee_id`, `to_employee_id`, `thread_key`
  via additive migration — already applied to Supabase live).
- **`2539128`** — Phase 7b: item-comment threads on tasks + MROs,
  reusing the 7a `thread_key` column. Zero SQL.
- **`7039de7`** — Phase 9a: service worker flipped to cache-first
  (28 precached files), rolling IDB warmer on login, pending-sync
  counter in the offline bar, `controllerchange` auto-reload.
- **`da1dc10`** — Phase 9b+9c: warmer extended to pull
  item_shares rows. Three recovery escape hatches:
  `?sw=off` URL killswitch, `/clear-sw.html` standalone page,
  admin-panel "Clear SW Cache" button.
- **`aadfdc1`** — SW version chip in admin panel overview
  (superuser only). Shows live SW cache name + state + pending
  count + online/offline. Field-test observability.

Rollback tag: **`pre-field-test-2026-04-13`** on both `HesKenY/CHERP`
and `HesKenY/CHERP-Backup`. If something breaks in the field test,
`git reset --hard pre-field-test-2026-04-13` + force-with-lease push
is the escape hatch.

Migration file for Phase 7a (already applied to live Supabase):
`migrations/2026-04-13_ownership_phase7a_messages.sql`.

Test suite: 3 smoke suites (store-smoke, screens-smoke, chat-smoke),
134 assertions total, all green. `node test/run-all.js`.

---

## 2. Pipe-R shipped today — the deck + the learning team

All in `HesKenY/CHERP-Backup` (primary) + `HesKenY/Pipe-R` (secondary).

### 2.1 Deck worklist items (commit `3768035`)

Three items from `.claude/WORKLIST.md` landed at once:

1. **Session-pinned output tray** — `.chat-tray` div below the
   chat log, always shows the latest non-pending assistant reply
   with a Copy button. Survives scroll position so the raw reply
   is always grabbable.
2. **Warm button** — new `Warm` button in the chat action row.
   Hits `POST /api/agent/warm { agentId }` → spawns
   `ollama run <base>` with stdin `"warm\n"` to load the model
   into Ollama's resident cache. Button states: Warm / warming /
   Warm ✓ (auto-fades after 30s).
3. **Chat scroll-position pin** — `state.chatStickToBottom` flag
   tracks proximity-to-bottom within 48px. renderChat only
   auto-scrolls when stuck. "New ↓" chip appears over the log
   when new content arrives while scrolled up. Tapping the chip
   jumps to bottom. Agent switch resets the pin state.

Bonus: fixed `server.js:170` — `git-status` command handler had
no `cwd`, inheriting whatever directory server.js was launched
from. When launched from `C:\Users\Ken\` it walked Windows legacy
junctions (`Application Data/`, `Cookies/`, etc.) and spammed
permission-denied warnings. Now explicitly `cwd: ROOT`.

### 2.2 Real stats engine (this commit)

Three new core modules under `agent_mode/core/`:

**`stats.js`** — programming-ability stats grounded in actual
training-log.jsonl outcomes. Every stat is real data, not
placeholder bars.

- `computeAgentStats(agentId)` — per-agent stats object
- `computeAllStats()` — bulk for the whole roster
- `getStatsCached(ttlMs)` — 2s cache for the dashboard endpoint
- `invalidateStatsCache()` — called after reviews

Stats shape (0–100 scale where applicable):
- **code** — approval rate on draft_patch / draft_test / implement
  / refactor / fix / patch tasks
- **recon** — approval rate on scan / analyze / map / investigate
  / trace
- **qa** — approval rate on review / audit / lint / test / critique
- **docs** — approval rate on summarize / document / learn / extract
- **speed** — inverse of median elapsed time (5s→100, 60s→50, 120s→10)
- **grit** — % of successes that completed on first attempt
- **volume** — log-scaled attempt count
- **xp** — weighted total across approved tasks
- **level** — derived via a soft polynomial curve (100/240/430/…)
- **class** — dominant archetype: Implementor / Pathfinder /
  Auditor / Archivist / Untested

XP rules: first-attempt approval gets a 1.25× bonus. Implementation
tasks score 30–40 XP, recon 15–20, docs 12–15, chat 3. Rejected
tasks score zero. Non-reviewed tasks score zero until someone
reviews them.

**`learning.js`** — per-agent learning event log. Every review
outcome (approve / reject / fail) appends a row to
`agent_mode/memories/<slug>/learning.jsonl`:

```
{ at, taskId, taskType, outcome, xpGain, elapsed, attempt, note, objective }
```

- `recordLearning(agentId, entry)` — non-throwing append
- `readLearning(agentId, limit)` — most-recent first
- `summarizeLearning(agentId, window=30)` — `{ count, approveRate,
  xpLast, trajectory }` where trajectory is `rising` / `falling`
  / `steady` based on comparing recent half vs. older half of the
  window.
- `summarizeAllLearning(agentIds, window)` — bulk for the deck

Wired into `POST /api/review` so every manual or auto-review
stamps an event. The stats cache is invalidated on each review.

**`dreams.js`** — offline reflection layer. The REM-sleep
equivalent for each agent. `dreamAgent(agent, opts)` runs the
agent's own base model against a structured prompt that summarizes
its last N training-log entries and asks it to produce four
sections: LEARNED / PATTERNS / QUESTIONS / GAPS. Response is
parsed into bullet arrays, appended to
`agent_mode/memories/<slug>/dreams.jsonl`, and strong insights
(learned + patterns, top 3 each) get stamped into the agent's
`notes.md` under a `## Dreamed YYYY-MM-DD` block. Since
`executor._buildPrompt()` injects notes.md on every task dispatch,
this closes the feedback loop — a dream's insights become
standing instructions for future work.

New endpoints on server.js:

- `POST /api/agent/warm { agentId }` — load model into Ollama
  resident cache (shipped with deck worklist items)
- `POST /api/agent/dream { agentId, windowSize? }` — fire a
  reflection pass (60–120s)
- `GET /api/agent/dream/:agentId` — recent dreams for an agent
- `GET /api/agent/learning/:agentId` — recent learning events +
  summary
- `GET /api/agent/stats` — bulk stats for all agents

### 2.3 Dashboard endpoint enrichment

`getDashboardState()` in server.js now stamps every agent with:
- `computedStats` — full stats object from stats.js
- `level` — real level number
- `xp` — total XP
- `computedClass` — dominant archetype
- `computedReadiness` — composite readiness 0–100
- `learning` — recent trajectory summary

These ride alongside the existing `hasNotes`, `notesLength`,
`chatTurns` memory stamps. All in the single `/api/dashboard` GET.

### 2.4 Deck renderer updates

`pipe-r.html`:

- `getAgentMetrics(agent)` — now prefers `agent.computedStats`
  when present. Falls back to placeholder heuristics for
  un-tested agents so a fresh roster still renders.
- `getAgentLevel(agent)` — prefers `agent.level` stamped by the
  server. Falls back to the placeholder curve.
- `renderSummary` stats tab — full new layout when computedStats
  is present: 4-stat top grid (Level / Class / XP / Readiness) +
  8 bars (XP-to-next / Code / Recon / QA / Docs / Speed / Grit /
  Volume) + 4-stat counts grid (Attempts / Approved / Rejected /
  Successes) + 4-stat recent-learning grid when events exist
  (Recent approvals / Recent XP / Events tracked / Trajectory
  badge). Legacy layout stays as the fallback.

---

## 3. Parallel Codex setup

As of 2026-04-13, this repo is worked by **two AI coding agents
in parallel**:

- **Claude** (this session) — folder `C:\Users\Ken\Desktop\Claude`
- **Codex** (OpenAI Codex CLI) — folder `C:\Users\Ken\Desktop\Codex`

Both folders are separate clones of the same repo sharing the same
git remotes (`origin` = HesKenY/CHERP-Backup, `pipe-r` =
HesKenY/Pipe-R). Coordination is **shared remote, shared main** —
no feature branches for routine work. Each folder has its own
working tree; agents don't touch each other's working tree directly.

**What's in the context pack:**

- `AGENTS.md` — coordination protocol, who reads what, pulling/pushing,
  working-tree isolation, handoff docs
- `.claude/CODEX_BRIEF.md` — consolidated port of Claude's
  auto-memory. Ken's user profile, voice rules, design principles,
  project ecosystem, security context, full phase history, meta-rules
- `.claude/HANDOFF_*.md` — this file and any future ones

**Who works on what (as of 2026-04-13):**

- Codex tends to work on Pipe-R deck layouts, model roster, visual
  polish, trainer deck rebuild. As of the start of this session
  Codex had 184 lines of uncommitted `pipe-r.html` work in its
  folder — adding new models to the deck.
- Claude tends to work on CHERP, store.js, schema migrations,
  service workers, Supabase plumbing, cross-project coordination,
  the squad's learning infrastructure.
- These are tendencies, not walls. `.claude/WORKLIST.md` is the
  coordination surface when work overlaps.

---

## 4. Log structure in Codex folder (gitignored — manual seed)

Ken asked for a per-agent log split inside `C:\Users\Ken\Desktop\Codex`:

```
.claude/logs/
├── claude.log        ← Claude's own session log (Claude writes here)
├── codex.log         ← Codex's own session log (Codex writes here)
└── shared.log        ← joint channel both agents append to
```

Since `*.log` is in `.gitignore`, these files DO NOT propagate via
git. Each agent writes to its own log in whichever folder it's
running from. To check if Codex has written anything new, open
`C:\Users\Ken\Desktop\Codex\.claude\logs\codex.log` directly.

**Shared log convention** — both agents append one-line entries:

```
2026-04-13T22:58:00Z [claude] Phase 9 stats engine shipped, pushed to main
2026-04-13T23:10:00Z [codex]  Adding new party slot for compiler agent
```

Keep entries terse — this is a notification feed, not a narrative.
For anything longer than one line, write a dated `HANDOFF_*.md`
instead.

---

## 5. Open threads / queued work

### 5.1 Immediate (field-test day 2026-04-13)

- **CHERP field test** — Ken + Sean run
  `.claude/plans/field-test-phase9-checklist.md` on real phones.
  Logs bugs, ideally via screenshots including the SW version chip
  in the admin panel.
- **Training flywheel** — Agent Mode is ON as of this session
  (`autoExecutePaused: false`). Queue has 6 pending-review tasks
  + 20 approved + 1 failed at handoff. The Auto Mode loop in the
  deck keeps the queue fed. Training-log grows with every task.

### 5.2 Next-session threads (no blockers)

- **Phase 7c** (CHERP) — retire team_code broadcasts, replace with
  channels-as-shared-items. PARKED pending the ID-system expansion
  conversation (whiteboard note in the session that created this
  handoff).
- **Phase 8** (CHERP) — home.js + mycrew.js fully on the share
  graph. No code started.
- **ID system expansion** (CHERP) — whiteboard plan to add Project
  layer above Crew, role/project/site broadcast routing, tags as
  secondary capabilities, Meshtastic bridge for field messaging.
  Ken parked this explicitly. Write
  `.claude/plans/cherp-identity-expansion.md` when we pick it up.
- **Phase 4.5** (CHERP) — Nest backend adapter. `NEST()` option
  in store.js as a parallel backend alongside Supabase. Pilot
  customers (JSBackyard + REVV) ship on Nest from day one. After
  phase 3 validated in the field.
- **Deck: next version** (Pipe-R) — Ken wants Codex to continue
  building this. Currently adding new models. Claude assists where
  it lands naturally.

### 5.3 Dream scheduling

`dreamAgent()` is plumbed but NOT fired automatically. A natural
next add: a cron-like loop in server.js that fires one dream per
agent every N hours, round-robin, whenever the agent has >12
unseen training-log rows since its last dream. Don't build this
unless Ken asks — the manual endpoint is enough for now.

### 5.4 Nothing is on fire

Field test is the near-term priority. Nothing in this handoff is
time-critical for tomorrow except Ken opening the recovery page on
at least one device to confirm it loads before the test starts.

---

## 6. How to verify the stats engine works

```bash
node --input-type=module -e "
  import('./agent_mode/core/stats.js').then(m => {
    console.log(JSON.stringify(m.computeAllStats(), null, 2).slice(0, 3000));
  });
"
```

Should print per-agent stats objects. At session end qwen2.5-coder
showed Level 2 / 207 XP / 33% code / class Pathfinder / 33 attempts.
ForgeAgent showed Level 1 / 0 XP / 0 approvals out of 19 attempts
(failing). Real data, no placeholders.

## 7. How to verify the dream system works

```bash
# Whoever is running the server:
curl -s -X POST http://localhost:7777/api/agent/dream \
  -H "Content-Type: application/json" \
  -d '{"agentId":"qwen2.5-coder:14b","windowSize":8}'
```

Returns `{ ok: true, entry: { learned, patterns, questions, gaps, raw } }`.
The agent's `notes.md` gets a new `## Dreamed YYYY-MM-DD` block
with the top 3 learned + top 3 patterns. Subsequent tasks dispatched
to that agent will see the dreamed insights in their system prompt
(because executor.js injects notes.md on every build).

Safe to run any time. Agents with zero recent tasks return
`{ ok: false, reason: "no recent tasks to dream about" }`.
