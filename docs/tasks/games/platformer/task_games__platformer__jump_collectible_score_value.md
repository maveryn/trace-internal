# `task_games__platformer__jump_collectible_score_value`

## Contract
1. Domain: `games`
2. Scene id: `platformer`
3. Public task id: `task_games__platformer__jump_collectible_score_value`
4. Supported `query_id` values: `jump_collectible_score_value`
5. Answer schema: `integer_value`
6. Annotation schema: `point_set`
7. Program schema: `sum(score(collectible) for collectible in jump_arc_collectibles); scene=platformer; scope=jump_collectible_score_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
