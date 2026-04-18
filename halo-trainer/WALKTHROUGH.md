# halo-trainer walkthrough

**the classroom manual.** agents read this top-to-bottom at the
start of each training session. it tells them what to do, what
order to do it in, and how to know they're done.

this is not optional reading — if the scoreboard shows you
failing a drill, re-read the relevant curriculum doc + the
exact drill JSON before asking ken to re-tune your prompt.

---

## day 1 — orientation

**read first, in order:**

1. `README.md` — who you are, who the other students are,
   what the loop is
2. `curriculum/01-reverse-engineering.md` — the PE format +
   section layout + what lives where in halo2.dll
3. `curriculum/02-implementation.md` — ctypes gotchas, the
   hunter shape, what patterns the grader expects
4. `curriculum/03-observability.md` — HUD parse rules, motion
   diff, activity labels
5. `curriculum/04-quality.md` — the three hard rules +
   failure taxonomy

**goal of day 1:** understand WHY the classroom exists and
WHERE you fit in. no drills today.

---

## day 2 — first drill pass

**run the full pass:**

```
cd halo-trainer
node src/enroll.js              # roll call — all 7 models ready?
node src/runner.js              # fires every drill in drills/
node src/scoreboard.js          # who passed, who failed
```

**expected first-pass outcomes** (baseline — ken saw this):

| student | track | score | notes |
|---|---|---|---|
| forgeagent:latest | integration | 100% | JSON patch tight and valid |
| qwen2.5-coder:14b | implementation | 100% | full ctypes scanner, 169s |
| cherp-piper:latest | reverse-engineering | 100% | halo2.dll base address + size |
| cherp-piper:latest | recon | 82% | install tree mapped; missed 1 rubric check |
| llama3.1:8b | observability | 88% | HUD parsed to JSON; 1 field short |
| jefferyjefferferson:latest | quality | FAIL | response drifted into QA role persona |

**if you see lower than 80%, re-read your curriculum doc
before the retry pass.**

---

## day 3 — retry + improve

```
node src/retry.js               # re-runs only the failures
node src/scoreboard.js          # did you climb?
```

**if you are jefferyjefferferson:latest** — the quality drill
fails because the model drifts into generic QA language
("Understood, I'll keep these in mind") instead of emitting
the structured markdown the rubric wants. the fix is ONE of:

- rewrite your response to start with `# god-mode write verification` exactly as a level-1 header
- include at least 8 bullet points
- explicitly name `ReadProcessMemory`, `ctypes`, `persist`, `clamp` in the body
- do NOT say "I cannot" or "I'll need more info"

re-read `drills/quality-101-write-verify.json` — the rubric
is right there. match it exactly.

---

## day 4 — the reverse-engineering track deep dive

(cherp-piper, qwen2.5-coder)

**chain of drills:**

1. `reverse-101-dll-base` — name the base address
2. `reverse-102-section-layout` — PE sections + where
   mutable state lives
3. `recon-101-install-tree` — MCC file layout
4. `recon-102-memory-budget` — how much do we scan

**reference material:**
- `../agent_mode/memories/ken-ai-latest/halo-game-dump.md`
  holds the local Codex-side MCC module list, updated every 5 minutes
  when the game_dumper loop is running
- `../agent_mode/memories/ken-ai-latest/halo-modules.jsonl`
  is the same data in one-json-per-line form

**what "good" looks like:**
- you can quote the exact hex base address of halo2.dll
- you can explain why `.data` is where the health float
  lives (mutable page, writable, unique per process)
- you can estimate the scan budget for a 12GB RW footprint
  (spoiler: don't scan regions > 256MB, don't scan regions < 4KB)

---

## day 5 — the implementation track

(qwen2.5-coder, forgeagent)

**chain of drills:**

1. `implementation-101-health-scanner` — the full ctypes
   delta scanner
2. `implementation-102-pin-thread` — the background writer
   thread
3. `integration-101-aimbot-tune` — propose a JSON patch
4. `integration-102-daemon-heal` — recover a dead daemon

**ctypes gotchas you MUST get right:**

```python
# wrong — will OverflowError on x64
hmods = (ctypes.c_void_p * 1024)()

# right
hmods = (wintypes.HMODULE * 1024)()

# wrong — no argtypes = default C ABI = pointer mangling
psapi.GetModuleBaseNameW(h, hmod, buf, 1024)

# right
psapi.GetModuleBaseNameW.argtypes = [
    wintypes.HANDLE, wintypes.HMODULE,
    wintypes.LPWSTR, wintypes.DWORD,
]
psapi.GetModuleBaseNameW.restype = wintypes.DWORD
psapi.GetModuleBaseNameW(h, hmod, buf, 1024)
```

**what "good" looks like:**
- code runs first try, no OverflowError
- ReadProcessMemory + VirtualQueryEx + WriteProcessMemory all present
- MBI is a ctypes.Structure with the correct field types
- handles 2M+ candidates without OOM

---

## day 6 — observability track

(llama3.1:8b, P0ryg0n Logdex)

**chain of drills:**

1. `observability-101-hud-parse` — raw OCR → structured JSON
2. `observability-102-activity-label` — classify from signals

**respond with JSON only.** no prose intro. no code fences.
no markdown headers. just the JSON object.

```
{"ammo_current": 27, "ammo_max": 60, "shield_pct": 1.0, "health": 85, "activity": "idle"}
```

the grader has `json_valid` as a weight-5 check. if your
response has fenced code blocks or prose, you lose 5 points
before the structure check even runs.

---

## day 7 — quality track

(jefferyjefferferson)

**chain of drills:**

1. `quality-101-write-verify` — the verification plan
2. `quality-102-regression-risks` — 12-bullet risk taxonomy

**voice rule for this track:** you are writing a checklist,
not a chat response. start with a level-1 header. use bullet
points. name the specific API calls and data structures.

**avoid:**
- "Understood, I'll keep these in mind"
- "I cannot perform this action"
- "Let me help you with that"

**instead, write:**
```
# god-mode write verification

## read-back checks

- immediate re-read via `ReadProcessMemory` on the same addrs
  after the write; value must match within epsilon 0.5
- ...
```

---

## day 8 — trainer track (ken-ai)

**you are the target.** every other drill feeds your fine-tune
corpus. your drills test whether you can produce in-voice
tactical calls and post-mortems.

**chain:**

1. `trainer-101-tactical-call` — pick the next action from a
   live tick state
2. `trainer-102-death-postmortem` — WIN/FAIL/NEXT in ken's
   voice

**voice rules — hard no's:**

- no "as an AI"
- no "think of it as" / "like a" — no analogies
- no construction metaphors (you are NOT a plumber today)
- no uppercase sentences
- no pleasantries

**voice rules — hard yes's:**

- lowercase only
- 4-10 words per line
- direct actions: "retreat cover plasma pistol" beats
  "I would recommend withdrawing to cover"
- typos ok

**example PASS response:**
```
ACTION: move_back
WHY: shield low, reload then re-engage
```

**example FAIL response:**
```
As an AI, I would recommend that you...
```

---

## day 9 — curation

```
ls corpus/                      # what's in the fine-tune pile
```

only drills that scored above their `passingPercent`
threshold land in `corpus/<curriculum>.jsonl`. that's the
Ken AI v2 fine-tune dataset. when curation is clean, you
can pipe corpus/*.jsonl into a real fine-tune job.

**not every passing row is ken-ai's voice.** trainer drills
are in ken's voice. other drills are structured markdown.
the fine-tune job should filter on `drillId` starting with
`trainer-` if you only want voice training.

---

## day 10+ — add drills

ken will add new drills based on what he sees in production.
each new drill is just another JSON file in `drills/`:

```json
{
  "id": "your-new-drill-id",
  "title": "one-line description",
  "student": "model:tag",
  "curriculum": "reverse-engineering",
  "contextFiles": ["../../relative/path/to/context.md"],
  "prompt": "the task for the model, explicit about format",
  "rubric": [
    { "type": "contains", "needle": "key_term", "weight": 2 },
    { "type": "regex", "pattern": "pattern", "flags": "i", "weight": 2 },
    { "type": "min_length", "value": 400, "weight": 1 },
    { "type": "must_not_contain", "needle": "I cannot", "weight": 2 }
  ],
  "passingPercent": 0.6,
  "timeoutMs": 120000
}
```

**rubric check types:**

| type | what it tests |
|---|---|
| `contains` | `needle` appears in response |
| `must_not_contain` | `needle` does NOT appear |
| `regex` | `pattern` + `flags` matches |
| `min_length` / `max_length` | response length bounds |
| `bullet_count_min` | at least N `-` or `*` bullets |
| `section_header` | `header` text appears (case-insensitive) |
| `json_valid` | response parses as JSON (or contains one) |

---

## common failure modes + cures

| symptom | cure |
|---|---|
| `spawnSync ollama ETIMEDOUT` | model cold — bump `timeoutMs` to 180000 or run `ollama run <model>` once by hand first |
| `I'm sorry, I can't assist` | rubric's `must_not_contain` catches this, but the underlying issue is the model hitting a safety filter. rewrite the drill prompt to sound less adversarial |
| drift into role persona (cherp-piper talks plumbing) | the orchestrator's SYSTEM wrapper is polluting. halo-trainer bypasses it — but if you see drift, the drill prompt is too open-ended. tighten it |
| JSON-invalid response | add `"must_not_contain": "```"` and `"regex": "^\\s*\\{"` checks — forces the model to skip the code fence wrapper |
| cold GPU contention | don't run drills while MCC is using the GPU — halo eats 11GB of 12GB VRAM and the models get evicted to CPU |

---

## the golden rule

**no drill is worth running if you don't know what "good"
looks like.** before you run a drill, re-read the rubric.
if the rubric doesn't describe your idea of "good," edit
the rubric BEFORE the run, not after. the scoreboard only
tells you about rubric adherence, not real-world usefulness.
keep those in sync by updating drills as you learn what
production needs.
