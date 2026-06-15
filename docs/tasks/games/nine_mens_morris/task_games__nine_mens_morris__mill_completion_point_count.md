# `task_games__nine_mens_morris__mill_completion_point_count`

## Contract
1. Domain: `games`
2. Scene id: `nine_mens_morris`
3. Public task id: `task_games__nine_mens_morris__mill_completion_point_count`
4. Supported `query_id` values: `white_mill_completion_point_count`, `black_mill_completion_point_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`

## Program Contract
`count(filter(empty_board_points, completes_mill(point, queried_color)=true)); scene=nine_mens_morris; scope=mill_completion_point_count`

The rendered board shows light and dark pieces on Nine Men's Morris
intersections. A mill is three same-color pieces on one straight board line.
For the queried color, the program counts empty board points where placing one
piece of that color would complete at least one mill, and annotates the center
point of every counted empty point.

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. The two semantic query ids differ only by queried piece color.
3. Annotation is projected from the same generated game state used for answer verification.
