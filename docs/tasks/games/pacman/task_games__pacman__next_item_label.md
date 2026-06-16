# `task_games__pacman__next_item_label`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__next_item_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `point`

## Program Contract
`label(first(route_item in labeled_bonus_items ordered by route_position)); scene=pacman; scope=next_item_label`

## Generation Notes
1. The highlighted route starts at the visible Pac-Man marker.
2. The answer is the label of the first visible labeled bonus item reached along the highlighted route.
3. Annotation is a scalar point at the selected bonus item center.
