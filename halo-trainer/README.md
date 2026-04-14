# halo-trainer

learning environment for ken-ai + the support squad. the goal
is not to "beat halo 2" — it is to build a repeatable loop:

1. **observe** the game — dump module state, read HUD, capture keypresses
2. **drill** agents on structured exercises — reverse engineering, tactical
   decisions, memory hunts
3. **score** their answers against known-good references
4. **curate** passing runs into the training corpus
5. **re-run** — each pass raises the scoreboard

this is a SEPARATE project from `agent_mode/halo/`. the hot path
(aimbot, keylog, drive loop) lives there. this folder is the
classroom. agents come here to learn, agent_mode/halo goes to
apply what they learned.

## layout

```
halo-trainer/
  curriculum/     lessons in markdown — one concept per file
  drills/         drill definitions (json) — task + expected output + scoring
  runs/           per-run outputs (jsonl) — one row per drill attempt
  corpus/         curated training rows — only the ones that passed review
  tools/          shared utilities — ollama spawn, scoring, extract
  reports/        scoreboard + progress snapshots
  logs/           raw stdout/stderr from tool runs
  src/            the trainer itself (runner.js, grader.js, enroll.js)
```

## who's enrolled

| id | slot | role in classroom |
|---|---|---|
| ken-ai:latest | trainer | the student we are building toward — all curricula point here |
| cherp-piper:latest | student | recon specialist — learns to map MCC memory |
| qwen2.5-coder:14b | student | implementation — learns to write ctypes + rust hunters |
| forgeagent:latest | student | integration — learns to stitch the reverse findings into the live loop |
| llama3.1:8b | student | observability — learns to read HUD + score engagements |
| jefferyjefferferson:latest | student | QA — learns to verify memory writes land + confirm god mode |
| m3w-learning:latest | tutor | tunes prompts after each drill based on what worked |

## the loop

```
enroll  → agents registered in src/registry.js
drill   → src/runner.js reads drills/*.json, fires each one
score   → src/grader.js checks output against reference
curate  → passing rows → corpus/*.jsonl
report  → src/scoreboard.js prints per-agent progress
```

each drill is idempotent. re-run the same curriculum 10 times
and the scoreboard shows which agent is improving, which has
plateaued, and which needs its prompt re-tuned.

## relationship to agent_mode/halo

| halo-trainer (here) | agent_mode/halo (live) |
|---|---|
| classroom | battlefield |
| scored exercises | unscored live loop |
| offline, no MCC required for most drills | requires MCC running |
| writes to corpus/ | writes to halo-memory.md |
| learning rate matters | latency matters |

the curation pipeline pulls the top-scoring rows from
`corpus/*.jsonl` into `agent_mode/training/training-log.jsonl`
so the Ken AI v2 fine-tune dataset only contains verified
quality work.
