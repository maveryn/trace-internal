# `task_games__pacman__path_pellet_count`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__path_pellet_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`

## Program Contract
`count(filter(route_cells, contains_normal_pellet=True)); scene=pacman; scope=path_pellet_count`

## Generation Notes
1. The highlighted route starts at the visible Pac-Man marker.
2. The answer counts only normal pellets whose cells lie on the highlighted route.
3. Annotation boxes enclose the counted normal pellets.
