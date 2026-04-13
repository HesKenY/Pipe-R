# Halo 2 MCC — tight reference for the learning agent

Pulled from halopedia.org + bungie.org legendary walkthroughs +
gamespot/strategywiki 2026-04-13. Terse by design — this file
flows into the Halo learning loop's prompt on every tick, so
every byte is priced in inference time.

## Default PC controls (MCC Halo 2 Anniversary)

```
W/A/S/D  = move          Space    = jump
LCtrl    = crouch        LShift   = sprint (Reach+ only)
LMB      = fire          RMB      = zoom / ADS
R        = reload        E        = interact / pick up
F        = grenade       Q        = melee
1        = weapon switch 2        = grenade type swap
4        = flashlight    C        = dual wield toggle
Tab      = scoreboard    Esc      = menu
```

The action vocabulary you emit maps directly to these keys.
Never invent a new action word — only the 20 in the loop list
are wired into the actuator.

## Weapon quick table

| weapon             | range    | role              | key tip                                           |
|--------------------|----------|-------------------|---------------------------------------------------|
| Battle Rifle (BR)  | med-long | primary           | 4-shot headshot. this is the gun.                 |
| SMG                | short    | spray             | weak alone; dual wield one + magnum               |
| Magnum             | short    | sidearm           | weaker than H1 pistol; pair with plasma pistol    |
| Shotgun            | melee    | close burst       | legendary flood room-clearer                      |
| Sniper Rifle       | long     | one-shot          | hold for elites; no-scope is 2 body shots         |
| Rocket Launcher    | any      | anti-vehicle      | hold for warthogs/wraiths/bosses only             |
| Plasma Pistol (PP) | med      | shield popper     | overcharge + BR headshot = "noob combo"           |
| Plasma Rifle       | short    | shield stripper   | dual wield pair for short range                   |
| Needler            | short    | tracking          | dual wield for supercombine vs elites             |
| Carbine            | long     | precision         | covenant BR; burst fire at 2/sec                  |
| Beam Rifle         | long     | covenant sniper   | overheat if you spam scoped shots                 |
| Brute Shot         | med      | arc grenade       | 4-shot mag; bounce around corners                 |
| Energy Sword       | melee    | lunge             | holds the map; lunges ~4m with RMB                |
| Fuel Rod Gun       | med      | green arc         | kills hunters in 1; grunts drop it                |
| Frag Grenade       | throw    | corner clearer    | bounces off walls                                 |
| Plasma Grenade     | throw    | sticky            | stick elites & vehicles, 4 sec fuse               |

## Enemy cheat sheet

- **Grunts** — the cannon fodder. Headshot them, watch them panic. Lowest priority in any fight.
- **Jackals** — shield bubble on the arm. Shoot the hand or go around. Snipers have purple plasma rifle sightlines — break them fast.
- **Drones** — flying, fragile. Frag grenades in formation. BR bursts.
- **Elites (Covenant, every color)** — shields first, then headshot. Red/gold = elite; white = stealth, listen for hum. PP overcharge + BR headshot. Swords at melee. They lunge — keep 3m buffer or get inside the lunge.
- **Hunters** — always in pairs. Shoot the orange exposed back/stomach. Tether melee each other after one dies. Sword oneshots from behind. Fuel rod oneshots from anywhere.
- **Brutes** (H2: Delta Halo onward) — shields in later games; H2 they're raw. Berserk when squadmate dies — sidestep the charge. Head/spine are weakpoints. Brute shot arcs.
- **Flood Infection** — popcorn, sprint through them; they pop on contact.
- **Flood Combat** — reanimated corpse with held weapon. Shotgun or sword. They soak body damage, go for the knee/groin sensor bulge.
- **Flood Carrier** — walking mine. Shoot from range, never melee.
- **Sentinels** — Forerunner bots. Plasma weapons strip shields fast. Ignore if you can; they don't chase.

## Universal tactics

- **Shields first, body second.** All covenant have shields that regen if left alone. Break shields → switch gun or reload → finish. PP overcharge nukes any shield in one burst.
- **Grenades > bullets against groups.** Count your grenades. You get 2 frags + 2 plasma max (4 total).
- **The noob combo** is the best single-target opener: PP overcharge (hold RMB until red) → release → while the enemy is shieldless, BR burst to the head. Works on every Elite.
- **Take cover between every exchange.** Shields regen in ~5s. Don't push wounded.
- **Crouch jump** — tap space then ctrl in the air. Adds ~1ft of reach. Matters for every boost.
- **Drop the AR.** The starting SMG/AR is useless past 5m. Pick up a BR or Carbine and never look back.
- **Stick the vehicle, not the driver.** Plasma grenade any Ghost/Wraith directly — the 4 sec fuse outlasts their escape.
- **Melee after reload.** Reload cancel: start reload, melee, reload resumes. Free damage on anything that gets in close.
- **Camo elites lunge in silence.** If the HUD flickers with a distortion and no sound, you're being stalked. Turn and swing melee early.

## Mission sketches (Halo 2 campaign order)

1. **Cairo Station** — Station defense. BR + magnum start. Hangar waves use PP+BR combo, 5 waves per bay. Final elevator has 6 elites — hold crates.
2. **Outskirts** — Covenant-occupied city. Rooftop snipe + Warthog run. Pick up BR immediately.
3. **Metropolis** — Bridge + Scarab setup. Hold the turret, board the Wraith.
4. **The Arbiter** — Stealth + sword. Arbiter's sword is your primary. Sentinels in the gas mine.
5. **Oracle** — Sentinel interior. Beam rifle ammo everywhere. Heretic leader at end.
6. **Delta Halo** — Open jungle. First real Carbine access. Honor guards appear.
7. **Regret** — Temple arena, Regret boss. Sword him during his pillar vulnerability windows.
8. **Sacred Icon** — First Flood mission. Shotgun + grenades mandatory. Sentinels + Flood brawl — let them fight each other.
9. **Quarantine Zone** — Flood horde. Scorpion tank segment.
10. **Gravemind** — Alternating Chief/Arbiter. Heavy Flood + Brute mix.
11. **Uprising** — Arbiter in the city, no Master Chief. Hold elite honor guard.
12. **High Charity** — Chief returns. Brutes + honor guards + Tartarus-adjacent. Gravemind cutscene.
13. **The Great Journey** — Arbiter + Hunters on your side. Boss: Tartarus. Sword the shield generators when his shields drop.

## When the HUD OCR is empty

Tesseract is cropping fractional HUD regions on a 5120x1440
ultrawide. Most ticks the state will be blank. When it is:

- Do NOT pick `noop`.
- Pick a MOVEMENT action (move_fwd / strafe / look_left) to
  generate visual delta so the next tick has something to OCR.
- Vary your movement — don't loop the same action forever. If
  your last 3 turns were all `look_left`, pick `move_fwd` or
  `strafe_right` this tick.
- The history block in each prompt shows the last 3 actions —
  use it to avoid self-loops.

## How you learn from yourself

Every tick you take is written to
`agent_mode/memories/ken-ai-latest/halo-log.jsonl`. Every 20
ticks the loop auto-fires a dream pass: your own model reads
the recent log and writes LEARNED / PATTERNS / QUESTIONS /
GAPS bullets into your dreams.jsonl. Strong learned+patterns
bullets get promoted into this file's companion `notes.md`
under a `## Dreamed YYYY-MM-DD` block, which then rides into
every future tick's prompt.

That IS the self-teaching loop. Your job is to TRY things so
the log has variety to learn from — if you always pick the
same action you have nothing to dream about.
