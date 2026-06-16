# `task_games__pacman__route_score_value`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__route_score_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_value`
6. Annotation schema: `point_set`

## Program Contract
`sum(score(collectible) for collectible in route_collectibles); scene=pacman; scope=route_score_value`

## Generation Notes
1. Normal pellets on the highlighted route score 1.
2. Printed-value bonus items on the highlighted route score their printed value.
3. Annotation points mark every normal pellet and printed-value bonus item included in the score.
