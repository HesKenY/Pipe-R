# Pipe-R / CHERP worklist — 2026-04-12 snapshot

Running punch list of what's live, what's next, and the Live Test Mode
design brief. Owner: Ken + Claude. Edit freely.

---

## 🟢 Live and working right now

- **Pipe-R deck** (`DECK.bat` → `pipe-r.html?deck=1`) — 1920×720 chromeless
  Chrome app window. Deck / Board tabs. Trainer with Ken AI pixel portrait.
- **Eight registered agents** — Ken AI, 5c1z0r, R0t0m, D3c1du3y3, P0ryg0n,
  Umbr30n, 4l4k4z4m (unblocked, slow cold start), M3w (built today).
- **Per-agent memory system** — `agent_mode/memories/<slug>/` with
  `notes.md`, `charter.md`, `chat-log.jsonl`. Injected into every chat
  turn AND every dispatched task via `executor._buildPrompt()`.
- **Chat panel** — tied to selected agent. Send/receive live against
  ollama, persists to disk + training-log.jsonl. Notes editor + disk Clear
  + training log Approve/Reject viewer.
- **Remote deck** (`remote.html`) — vertical stack mirroring the deck.
  PIN `0615`. Galaxy Fold 6 breakpoints (≤420, ≤720, ≥721). Hidden
  until unlocked.
- **Android WebView wrapper** — `C:\Users\Ken\Desktop\PipeR-Remote-Android`.
  Default URL `http://192.168.0.58:7777/remote.html`. Error overlay shows
  connection failures instead of black-screen. Gradle wrapper in place;
  Studio can sync on open.
- **CHERP** — `crew_tasks` 400 save bug fixed and pushed to `main`. Live.
- **Training log flywheel** — chat turns + dispatches both feed
  `training-log.jsonl` with `taskType: "chat"` / other. `curate.js`
  filters. Approve/Reject review rows in the deck.

---

## 🟡 Near-term worklist (1-3 sessions each)

### Agent Mode: LIVE TEST MODE  (high priority, designed below)
Split the party in half. Three agents roleplay a crew on a target CHERP
instance, three agents maintain it. Detailed brief in the next section.

### Deck: session-pinned model output tray
Chat shows latest assistant reply but old turns scroll up. Add an
always-visible "last output" tray so Ken can grab the raw text without
scrolling. Small UI add, big ergonomics win.

### Deck: 4l4k4z4m warm-start button
Alakazam takes ~90s cold. Add a "Warm Up" action that fires a one-line
probe so the model is resident when a real task lands. Same for M3w /
cherp-piper — any model that gets evicted.

### Hub.js: bring the deck control surface into the TUI
Currently hub has no button to trigger chat, view memory, or run the
training viewer. Add: `M → C` (chat with selected agent), `M → L` (view
training log for selected agent), `M → R` (approve/reject most recent).

### Remote deck: notes + training view on phone
Right now the phone can only chat. Mirror the Notes editor + Log viewer
from the deck so Ken can tune agents from a couch.

### Android app: pre-wired LAN discovery
Instead of a hardcoded `192.168.0.58`, scan the /24 subnet for
`http://<ip>:7777/api/dashboard → 200` on first run. Skip the manual
URL entry step entirely.

### Jefferferson retry budget
Tune executor timeouts per agent — some models (Alakazam) need 120s
on cold start. Add `agent.timeoutHints = { scan: 60, summarize: 90 }`
in agents.json so per-task-type timeouts can override the global.

---

## 🔵 Medium-term (blocked on something else)

- **Ken AI v2 real fine-tune** — needs ≥200 curated rows in
  `training-log.jsonl`. Currently at 119 entries, 2 of which are chat.
  Live Test Mode will flood the log.
- **CHERP sheet_url column + "View in Sheets" button** — waiting on
  the Sheets sync feature to be production-stable.
- **Nest dependency install hook** — Nest wizard should detect/install
  Node.js etc. Blocked on needing more concrete test customers first
  (JSBackyard + REVV queued).
- **CHERP home-screen realtime** — partial Supabase realtime now
  working; home.js still needs to subscribe to mycrew and auto-refresh.
- **Jefferferson voice rebuild** — it's a stock memory-curator model
  with no personality layer. Build a dedicated profile + Modelfile
  like Ken AI / M3w if we keep using it beyond pattern-matching.

---

## 🔴 Known issues still open

- **Android app** has not been verified to build/run yet — only
  the file scaffold exists, Studio sync + Run has not been driven to
  a successful APK on a device.
- **`chat-log.jsonl` from earlier sessions** may contain ANSI spinner
  residue from before the scrub landed. Harmless but ugly.
- **CHERP `safety.js`** has an unreviewed ACE Pricing weather spike
  modification that's deferred. Not touching until promoted.
- **Auto-refresh on the deck** polls `/api/dashboard` every 5s — cheap,
  but the chat panel re-render fights the log scroll position if a new
  message lands mid-read. Pin scroll when user has scrolled up.

---

## === LIVE TEST MODE ===

**Goal:** Prove CHERP against a real-feeling construction workflow by
having the six-agent party split into two opposing teams — one uses the
product, one keeps it alive — against a specific CHERP instance URL Ken
provides.

### Team split

Half the party = **Crew Roleplay** (Team A), the other half = **Ops +
Maint** (Team B). The trainer (Ken AI) coordinates both. M3w watches
from the companion lane and feeds lessons back.

**Team A — Crew Roleplay (3 agents)**
- **D3c1du3y3 Pathfinder** — Foreman. Reads the CHERP app, maps the
  flows, assigns work, sets priority.
- **5c1z0r Patchsmith** — Worker. Clocks in/out, updates task progress,
  uploads photos, adds notes.
- **P0ryg0n Logdex** — Apprentice + incident reporter. Does the boring
  tasks, surfaces weird app behavior as "site reports."

**Team B — Ops + Maint (3 agents)**
- **R0t0m Relay** — Integration ops. Watches HTTP, Supabase schema,
  restarts services, wires new tables, handles the deploy loop.
- **Umbr30n Safeguard** — QA. Reproduces bugs Team A reports, writes
  regression notes, blocks bad releases.
- **4l4k4z4m Archive** — Memory curator. Snapshots what worked, what
  broke, and updates the team's shared notes.md after each round.

**Trainer + companion**
- **Ken AI** — Referees both teams. Picks priorities, breaks ties.
- **M3w Promptdex** — Observes the whole round, proposes prompt /
  notes changes based on what actually happened.

### Inputs

1. **CHERP instance URL** — default `https://cherp.live/demo.html` (set 2026-04-12 by Ken). Intended to validate customer instances before field deploy.
2. **Scenario seed** — "4-man crew, 3-day kitchen remodel" etc.
3. **Round length** — default 30 minutes of wall time per sim round.
4. **Repeat count** — default 3 rounds per session.

### Round loop

```
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Ken AI reads the scenario + instance URL             │
  │                                                          │
  │ 2. Team A kickoff (parallel):                            │
  │    - D3c1du3y3 hits /api/dashboard-ish CHERP endpoints   │
  │    - Creates crew, joins members, schedules tasks        │
  │    - 5c1z0r clocks in, updates progress, uploads photo   │
  │    - P0ryg0n writes field reports, flags anomalies       │
  │                                                          │
  │ 3. Team B watchdog (parallel to Team A):                 │
  │    - R0t0m polls health + diffs schema                   │
  │    - Umbr30n replays P0ryg0n's anomalies                 │
  │    - 4l4k4z4m writes the round summary                   │
  │                                                          │
  │ 4. Ken AI + M3w debrief                                  │
  │    - What worked, what broke, what's the next fix        │
  │    - Output: prompt changes, notes.md updates, bug list  │
  │                                                          │
  │ 5. Ken reviews the debrief packet from the deck          │
  └─────────────────────────────────────────────────────────┘
```

### What the deck button needs to do

**UI**
- New panel in the deck's Board tab called **Live Test**
- Input field: CHERP instance URL
- Dropdown: scenario seed (preset list, plus "custom")
- Slider or number: round length (5 / 15 / 30 / 60 min)
- Big green button: **Start Round**
- Live board showing Team A + Team B status per agent
- Debrief area where the latest round summary lands

**Backend**
- New module `agent_mode/core/livetest.js` that:
  - Loads a scenario definition (task list, crew roles, timing)
  - Builds a task packet per agent with their specific role +
    the CHERP URL
  - Dispatches the whole batch in parallel via `/api/dispatch`
  - Polls for completion, aggregates results
  - Runs the debrief step: Ken AI + M3w read everyone's output,
    produce a summary that's persisted to
    `agent_mode/livetest/rounds/<timestamp>.md`
  - Auto-reviews each agent's output (approve/reject in training log)
- New endpoint `POST /api/livetest/start` with the params above
- New endpoint `GET /api/livetest/rounds` for the deck's history list
- New endpoint `GET /api/livetest/rounds/:id` for the debrief packet

**Scenario format** (`agent_mode/livetest/scenarios/*.json`)
```json
{
  "id": "kitchen-remodel-3day",
  "name": "3-day kitchen remodel, 4-man crew",
  "team": {
    "foreman": { "name": "J. Sim-Heath", "agent": "cherp-piper:latest" },
    "worker1": { "name": "A. Sim-Deibel", "agent": "qwen2.5-coder:14b" },
    "apprentice": { "name": "P. Sim-Poryg", "agent": "llama3.1:8b" }
  },
  "day1Tasks": [
    { "title": "demo old cabinets", "priority": "urgent", "assignTo": "worker1" },
    ...
  ],
  "durationMin": 30,
  "acceptCriteria": [
    "all tasks created",
    "at least one photo upload",
    "timecards match clock-in/out",
    "no client-side errors surfaced in P0ryg0n's field report"
  ]
}
```

**Harness choices to make before building**
1. **CHERP auth for the agents** — do they create real user_profiles
   rows via the signup flow, or do we seed fake PIN users ahead of
   time? Cheaper to seed. Also avoids RLS pain.
2. **Isolation** — do we spin up a dedicated test crew code like
   `SIM-01` for each round, or do we share a running instance? Probably
   dedicated per round with a cleanup step.
3. **HTTP client** — the agents are Ollama models, they don't browse.
   Team A has to drive CHERP via the Supabase REST API directly (SB_URL
   + SB_KEY calls, same as the live app) rather than through the HTML.
   That's a real test of the data layer but NOT a real test of the UI.
4. **UI-layer test** — for that we'd need a real browser driver
   (Playwright?) on a separate rail. Defer to v2.
5. **Bug reports** — P0ryg0n's "field reports" go where? Proposal: a
   new `agent_mode/livetest/incidents.jsonl` that Team B polls.
6. **Scoring** — does each round get a pass/fail grade? Proposal: yes,
   a simple `acceptCriteria` list in the scenario and Ken AI grades it
   at debrief time.
7. **Rate limiting** — parallel dispatch to 6 agents at once may thrash
   Ollama. Stagger with 5-10s between spawns.

### v0 scope (first build)

Just enough to prove the pipeline works end-to-end:
- One hardcoded scenario (kitchen remodel)
- Manual trigger from the deck (button → POST)
- 3 agents on Team A directly POST to CHERP's REST API
- 3 agents on Team B poll and write to incidents.jsonl
- One debrief round
- Summary written to disk
- No scoring, no cleanup

### v1 scope (after v0 proves out)

- Multiple scenarios, dropdown in the deck
- Per-round cleanup (delete the sim crew + tasks)
- Pass/fail grading with acceptCriteria
- Training log auto-review (Team B's output marks Team A's inputs
  approved/rejected)
- Round history browser in the deck

### v2 ideas (if v1 feels useful)

- Playwright UI driver for real browser tests
- Multi-instance mode: run Team A against one CHERP, Team B against
  a mirror, diff the results
- Crowdsourced scenarios from real customer complaints
- "Chaos" mode: Team B intentionally breaks things mid-round and
  measures how fast Team A notices

---

## Open questions for Ken

1. **Live Test Mode target** — start against `cherp.live` (production,
   risky) or a preview URL (safer, less realistic)?
2. **Auth strategy** — seed PIN users ahead of time or have agents
   "sign up" through the real flow?
3. **Android app** — test on the emulator first or straight to the
   Galaxy Fold 6?
4. **Alakazam's slow cold start** — worth replacing its base model
   with something lighter, or keep it for the cold-start penalty?
5. **Next agent to personality-tune** — Ken AI is done, M3w is done.
   Which specialist gets a custom profile.md + Modelfile next?

---

Last updated: 2026-04-12 by Claude Opus 4.6 (Pipe-R session)
