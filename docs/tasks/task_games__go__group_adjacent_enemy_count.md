# `task_games__go__group_adjacent_enemy_count`

## Contract
1. Domain: `games`
2. Scene id: `go`
3. Public task id: `task_games__go__group_adjacent_enemy_count`
4. Supported `query_id` values: `marked_group_adjacent_enemy_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(stones, adjacent_to_group(stone, marked_group) and stone_color=opponent_color)); scene=go; scope=group_adjacent_enemy_count; query_branch=marked_group_adjacent_enemy_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
