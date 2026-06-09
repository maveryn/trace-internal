# `task_games__dominoes__second_play_candidate_count`

## Contract
1. Domain: `games`
2. Task group: `dominoes`
3. Scene id: `dominoes`
4. Public task id: `task_games__dominoes__second_play_candidate_count`
5. Supported `query_id` values: `second_play_candidate_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(domino_tiles, can_play_second_after_marked_first(tile)=True)); scene=dominoes; scope=second_play_candidate_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
