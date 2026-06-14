# `task_games__pacman__pellet_count_before_ghost`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__pellet_count_before_ghost`
4. Supported `query_id` values: `pellet_count_before_ghost`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(prefix(route_cells, before=first(route_cell where contains_ghost=True)), contains_normal_pellet=True)); scene=pacman; scope=pellet_count_before_ghost`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
