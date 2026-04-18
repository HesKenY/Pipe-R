# Factorio AI — game memory

Durable memory for Factorio training. Updated by the trainer
and death-learning system. Scanned by the drive prompt.

## current_save

- unknown — detect via save file mtimes

## recipes_mastered

(populated as KenAI successfully uses recipes)

## ratios_learned

- 3 copper cable assemblers : 2 green circuit assemblers
- 48 stone furnaces fill 1 yellow belt (15 items/sec)
- 1 boiler : 2 steam engines
- 1 offshore pump : 20 boilers

## deaths_log

(populated by death-learning system — biter attacks, train hits, etc)

## tactics_learned

(populated after each failure analysis)

## blueprints_designed

(populated as KenAI creates successful factory layouts)

## research_history

(populated as research completes)

## bottlenecks_found

(populated by the optimization loop when production stats show starvation)
