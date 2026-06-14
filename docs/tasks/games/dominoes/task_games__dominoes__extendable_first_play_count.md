# `task_games__dominoes__extendable_first_play_count`

## Contract
1. Domain: `games`
2. Scene: `dominoes`
3. Scene id: `dominoes`
4. Public task id: `task_games__dominoes__extendable_first_play_count`
5. Supported `query_id` values: `extendable_first_play_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(domino_tiles, can_extend_chain_after_first_play(tile)=True)); scene=dominoes; scope=extendable_first_play_count`

## Program Contract
- `count(filter(domino_tiles, can_extend_chain_after_first_play(tile)=True)); scene=dominoes; scope=extendable_first_play_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
