# `task_games__reversi__frontier_disc_count`

## Program Contract

- Domain: `games`
- Scene: `reversi`
- Public task id: `task_games__reversi__frontier_disc_count`
- Supported `query_id` values: `black_frontier_disc_count`, `white_frontier_disc_count`
- Answer schema: `integer_count`
- Annotation schema: `point_set`
- Program schema: `count(filter(discs(query_color), touches_empty_neighbor)); scene=reversi; scope=frontier_disc_count`
- Program code: `count.filter.reversi_frontier_discs`
- Scalar annotation checked: `true`

## Generation Notes

- A frontier disc is a queried-color disc adjacent horizontally, vertically, or diagonally to at least one empty board cell.
- `black_frontier_disc_count` counts black frontier discs; `white_frontier_disc_count` counts white frontier discs.
- Annotation points are the centers of all counted frontier discs.
- The answer and annotation are bound from the same generated board state.
