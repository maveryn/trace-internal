# `task_games__pacman__route_score_value`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__route_score_value`
4. Supported `query_id` values: `route_score_value`
5. Answer schema: `integer_value`
6. Annotation schema: `point_set`
7. Program schema: `sum(score(collectible) for collectible in route_collectibles); scene=pacman; scope=route_score_value`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
