# `task_games__go__group_adjacent_enemy_count`

## Contract
1. Domain: `games`
2. Scene: `go`
2. Scene id: `go`
3. Public task id: `task_games__go__group_adjacent_enemy_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(stones, adjacent_to_group(stone, marked_group) and stone_color=opponent_color)); scene=go; scope=group_adjacent_enemy_count`

## Program Contract
- `count(filter(stones, adjacent_to_group(stone, marked_group) and stone_color=opponent_color)); scene=go; scope=group_adjacent_enemy_count`

## Generation Notes
1. The task samples a marked black or white connected group and asks for opponent stones touching it orthogonally.
2. `query_id=single` is the public no-branch query id; the prompt query key remains the semantic prompt template.
3. Annotation is projected from the same generated game state used for answer verification.
