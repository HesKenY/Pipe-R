# Halo 2 — mission progress tracker

THE GOAL of Ken's Halo 2 run: finish the campaign. Every
mission clear is a milestone and gets stamped here. This
file is the source of truth for KenAI's mission state —
when the UI asks "what's the current mission" or "how many
done" it comes from here via the brain FTS.

Status values:
- `locked`     — not reachable yet
- `in-progress` — currently being played
- `complete`   — mission-complete screen reached
- `skipped`    — Ken chose to skip (legendary gate, etc)

## Missions (Halo 2, in order)

| # | mission | status | first_started | completed_at | deaths | aimbot_shots | notes |
|---|---|---|---|---|---|---|---|
| 00 | The Heretic (Cairo Station prologue) | locked | — | — | — | — | cinematic tutorial |
| 01 | The Armory | locked | — | — | — | — | basic weapon training on Cairo |
| 02 | Cairo Station | locked | — | — | — | — | first real combat — sword elites + MA5B + BR |
| 03 | Outskirts | locked | — | — | — | — | first mission as Arbiter is next |
| 04 | Metropolis | locked | — | — | — | — | the scarab gun setup |
| 05 | The Arbiter | locked | — | — | — | — | arbiter intro, Oracle |
| 06 | The Oracle | locked | — | — | — | — | Gravemind reveal |
| 07 | Delta Halo | locked | — | — | — | — | jungle, sentinels |
| 08 | Regret | locked | — | — | — | — | prophet of regret boss |
| 09 | Sacred Icon | locked | — | — | — | — | flood introduction |
| 10 | Quarantine Zone | locked | — | — | — | — | sentinel enforcer fight |
| 11 | Gravemind | locked | — | — | — | — | mid-game climax |
| 12 | Uprising | locked | — | — | — | — | elite uprising |
| 13 | High Charity | locked | — | — | — | — | brute introduction |
| 14 | The Great Journey | locked | — | — | — | — | final mission, scarab boss |

## Current run state

<!-- Updated by tools/halo_missions.py on each start/complete event -->
<!-- Queried by /api/halo/missions/status -->

```yaml
current_mission: null
current_started_at: null
current_deaths: 0
current_aimbot_engagements: 0
total_missions_complete: 0
total_session_minutes: 0
game_complete: false
```

## How mission state changes
1. Ken clicks **Start Mission** in the Halo tab → the next
   `locked` mission flips to `in-progress`, timestamps open,
   and the aimbot + Pipe-R learning stack start logging.
2. While playing: keylog + aimbot log + vision HUD reads
   all append to `brain/corpus/halo_tools_logs/` and
   `brain/sessions/<date>/halo-run.jsonl`.
3. Ken reaches the mission-complete screen in game and
   clicks **Mark Complete** in the Halo tab → mission flips
   to `complete`, `completed_at` stamps, the row picks up
   the death count + aimbot engagement count from the
   session delta, the NEXT mission unlocks.
4. When mission #14 (The Great Journey) completes,
   `game_complete` flips to `true` and the UI shows the
   game-complete celebration screen.

## Mission-complete celebration — what happens on each clear

- Big green banner in the Halo tab showing the mission
  name + run stats (duration, deaths, aimbot shots fired,
  top confidence, any god-mode events)
- Row stamped into `brain/sessions/<date>/session_log.md`
- New entry in `brain/corpus/mission_clears.jsonl` (one
  row per clear, fed into training corpus as positive
  signal)
- KenAI drops a victory line in the chat in its own voice
  (lowercase, 4-10 words, no analogies)

## Why this file exists in the brain and not in a db

The brain uses markdown as source of truth so Ken can
read + edit it by hand. The SQLite FTS is a cache. If
Ken wants to manually flip a mission to `complete`
(e.g., he already beat it on another save), he can
edit this file directly and `/api/brain/rebuild` picks
it up.
