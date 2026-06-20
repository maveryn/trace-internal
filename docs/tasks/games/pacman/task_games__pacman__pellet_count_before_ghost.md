# `task_games__pacman__pellet_count_before_ghost`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__pellet_count_before_ghost`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set_map`

## Program Contract
`count(filter(prefix(route_cells, before=first(route_cell where contains_ghost=True)), contains_normal_pellet=True)); scene=pacman; scope=pellet_count_before_ghost`

## Generation Notes
1. The highlighted route starts at the visible Pac-Man marker.
2. The answer counts normal pellets before the first ghost encountered on that highlighted route.
3. Annotation uses `counted_pellets` for counted pellet center points and `first_ghost` for the stopping ghost center point.
