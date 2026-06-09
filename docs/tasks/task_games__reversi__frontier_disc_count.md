# `task_games__reversi__frontier_disc_count`

## Contract
1. Domain: `games`
2. Task group: `reversi`
3. Scene id: `reversi`
4. Public task id: `task_games__reversi__frontier_disc_count`
5. Supported `query_id` values: `black_frontier_disc_count`, `white_frontier_disc_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(discs(query_color), touches_empty_neighbor)); scene=reversi; scope=frontier_disc_count`

## Generation Notes
1. A frontier disc is adjacent horizontally, vertically, or diagonally to at least one empty board cell.
2. Annotation points are projected at the centers of all counted frontier discs.
3. The sampler uses reachable Reversi board states and rejects until the requested frontier count is exact.
