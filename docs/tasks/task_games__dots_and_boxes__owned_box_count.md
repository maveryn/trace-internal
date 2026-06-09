# `task_games__dots_and_boxes__owned_box_count`

## Contract
1. Domain: `games`
2. Task group: `dots_and_boxes`
3. Scene id: `dots_and_boxes`
4. Public task id: `task_games__dots_and_boxes__owned_box_count`
5. Supported `query_id` values: `player_a_owned_box_count`, `player_b_owned_box_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(completed_boxes, owner_mark(box)=queried_player)); scene=dots_and_boxes; scope=owned_box_count`

## Generation Notes
1. The scene renders a visible dots-and-boxes board with completed boxes marked by player `A` or player `B`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
