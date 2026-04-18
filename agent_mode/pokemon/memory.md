# Pokemon Crystal AI — game memory

## goal
Beat the Elite Four. Complete the game.

## current_state
- appears to be stuck cycling between main menu and exploring overworld.
- need to PROGRESS past the current screen, not loop.

## current_mission (from operator)
- **OBJECTIVE: GO TO A POKEBALL.** navigate to any visible pokeball on screen or in the environment.
- if in overworld: walk toward items / tall grass / buildings that contain pokeballs (pokecenter, prof elm's lab, pokemart).
- if in battle: use pokeball item from the bag to catch the pokemon (this requires menu navigation).
- if at a menu or dialog: advance through it (b for text, a for confirming selections) to get back to overworld.
- don't repeat a button if nothing changes. try a direction. walk toward visible objects.

## if_game_is_not_advancing
we are stuck. last few ticks cycled between main menu and overworld with no real progress.
try this EXACT sequence of button names (use one per tick, IN ORDER):
1. down       (menu cursor down toward Continue or Start)
2. down       (in case it was on New Game, now on Continue)
3. a          (confirm selection, should start the game)
4. b          (skip intro text if any appears)
5. b          (keep skipping)
6. b          (keep skipping)
7. down       (move character south to exit room / approach NPC)
8. down
9. down
10. a         (interact with NPC if one is in front of you)

if none of this helps after 10 ticks, try: start → down → down → a (open menu, scroll to save, save game).

the action vocabulary is EXACTLY: a b start select up down left right noop.
output ONLY one word from that vocab. no prose, no quotes, no periods.

## team
(populated as pokemon are caught/evolved)

## gym_progress
- [ ] Falkner (Violet City) — Flying
- [ ] Bugsy (Azalea Town) — Bug
- [ ] Whitney (Goldenrod City) — Normal
- [ ] Morty (Ecruteak City) — Ghost
- [ ] Chuck (Cianwood City) — Fighting
- [ ] Jasmine (Olivine City) — Steel
- [ ] Pryce (Mahogany Town) — Ice
- [ ] Clair (Blackthorn City) — Dragon
- [ ] Elite Four

## type_chart_key
- water beats fire/ground/rock
- fire beats grass/ice/bug/steel
- grass beats water/ground/rock
- electric beats water/flying
- ground beats fire/electric/poison/rock/steel
- ice beats grass/ground/flying/dragon
- fighting beats normal/ice/rock/dark/steel
- psychic beats fighting/poison
- dark beats psychic/ghost
- dragon beats dragon

## starter_guide
- totodile (water): strong early game, evolves into feraligatr
- cyndaquil (fire): good special attacker, evolves into typhlosion
- chikorita (grass): defensive, harder early game

## key_strategy
- always have type coverage across team
- grind 2-3 levels above gym leader's strongest
- save before gym battles and rival fights
- catch pokemon for HM slaves (cut, surf, strength, fly)
- money: buy potions early, save for ultra balls later

## deaths_log
(populated by death-learning — whiteouts, lost battles)

## tactics_learned
(populated after each failure analysis)

## route_knowledge
(populated as areas are explored)
