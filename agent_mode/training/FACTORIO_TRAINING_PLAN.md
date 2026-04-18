# Factorio Training Program — KenAI

## Why Factorio

Factorio teaches the same skills as software development:

| Factorio | Software |
|---|---|
| Factory layout | System architecture |
| Throughput ratios | Performance optimization |
| Blueprints | Code reuse / abstractions |
| Belt logistics | Data flow / pipelines |
| Research tree | Dependency management |
| Power grid | Infrastructure / scaling |
| Pollution / biters | Technical debt / security threats |
| Circuit networks | Event-driven programming |
| Train networks | Microservices / routing |
| Modular design | Clean code / separation of concerns |

Halo trains reflexes. Factorio trains the architect brain.

## Training Phases

### Phase 1: Game File Scanner (like Halo)
- Scan Factorio install directory for save files, mods, config
- Parse save files for factory state (Factorio saves are zipped Lua tables)
- Extract: research progress, production stats, map seed, mod list
- Write knowledge to `factorio-game-knowledge.json`

### Phase 2: Vision + OCR Loop
- Screenshot the Factorio window (same pattern as halo_tick.py)
- OCR the HUD: research queue, resource counts, alerts, minimap
- Motion detection for biter attacks
- Activity classification: building / researching / defending / exploring / idle

### Phase 3: Input Control
- Factorio accepts keyboard + mouse input same as Halo
- Key actions: WASD move, click place/remove, R rotate, Q pipette,
  E open inventory, Alt info overlay, Space shoot, Tab map
- Blueprint placement via hotbar slots
- Research queue via tech tree

### Phase 4: Strategic Planner
- Unlike Halo's tick-by-tick reflexes, Factorio needs PLANNING
- KenAI should think in goals, not individual actions:
  - "I need to produce 30 green circuits/min"
  - "That requires 3 copper cable assemblers + 2 green circuit assemblers"
  - "I need to route copper plates from smelting to cable line"
- The planner breaks goals into build steps
- Each step becomes a sequence of mouse/keyboard actions

### Phase 5: Death-Learning (Biter Attacks)
- Factory gets attacked → analyze what failed
- Not enough turrets? Wrong placement? No ammo production?
- Log the failure, store the fix, apply next time
- Over time: learns optimal defense patterns

### Phase 6: Optimization Loop
- Monitor production statistics (Factorio has built-in graphs)
- Identify bottlenecks: which machines are starving? which belts are full?
- Propose fixes: add more smelters, split belt, add train stop
- This is the core "architect brain" training

### Phase 7: Blueprint Library
- KenAI designs blueprints from experience
- Stores them as reusable patterns (like code libraries)
- Grades them by throughput efficiency
- Best blueprints become part of the training corpus

## Corpus Categories for Factorio

```
factorio_ratios      — "how many copper cable assemblers per green circuit?"
factorio_logistics   — "when should i switch from belts to trains?"
factorio_defense     — "biters keep breaking through south wall. fix?"
factorio_power       — "my factory is brownout. solar or nuclear?"
factorio_circuits    — "how do i wire a train station to only load when full?"
factorio_blueprints  — "design a 4-lane balanced smelting array"
factorio_research    — "what should i research first for green science?"
factorio_debug       — "trains are deadlocking at intersection. why?"
factorio_scaling     — "i need to 10x iron production. approach?"
factorio_deathlearn  — "biters destroyed my power plant. analysis + fix"
```

## Technical Stack

```
factorio_scanner.js  — game file parser (saves, config, mods)
factorio_tick.py     — vision + OCR (same pattern as halo_tick.py)
factorio_do.py       — action executor (same pattern as halo_do.py)
factorio_planner.js  — strategic goal → action sequence planner
factorio_trainer.js  — coaching loop (90s), reviews production stats
factorio_memory.md   — learned patterns, blueprints, failures
```

## Data Sources

- Factorio Wiki (factorio.com/api) — recipe data, ratios, entity specs
- Save file parsing — actual factory state
- Production statistics — in-game graphs read via OCR or mod
- Console commands — Factorio has `/c` Lua console for reading game state

## Mod-Assisted Training (Optional)

Factorio has a rich Lua modding API. A training mod could:
- Expose game state via RCON (remote console) instead of OCR
- Provide exact entity positions, belt contents, power draw
- Accept build commands programmatically
- Log every event (biter attack, research complete, etc.)

This would be 100x more reliable than OCR and enable much faster
training cycles. Build the mod after the vision-based prototype works.

## Implementation Order

1. Install Factorio (Steam or standalone)
2. Build factorio_scanner.js — read game files for knowledge
3. Build factorio_tick.py — vision capture
4. Add Factorio corpus prompts to the training pipeline
5. Build factorio_do.py — action executor
6. Build the strategic planner
7. Test: can KenAI start a new game and get to green science?
8. Iterate: add optimization, defense, trains, circuits
9. Optional: build the training mod for RCON-based control

## Success Criteria

- KenAI can start a fresh Factorio game and reach rocket launch
- KenAI can identify and fix production bottlenecks
- KenAI designs efficient blueprints from scratch
- KenAI defends against biter attacks without losing infrastructure
- Every failure makes the next run smarter (death-learning)
- Skills transfer: factory optimization patterns improve code architecture decisions
