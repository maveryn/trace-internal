# `task_games__hex__candidate_neighbor_count`

## Contract
1. Domain: `games`
2. Task group: `hex`
3. Scene id: `hex`
4. Public task id: `task_games__hex__candidate_neighbor_count`
5. Supported `query_id` values: `red_neighbor_count`, `blue_neighbor_count`, `empty_neighbor_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(adjacent_cells(reference_cell, requested_state)); scene=hex; scope=candidate_neighbor_count`

## Generation Notes
1. The reference cell is labeled in the rendered board and is not counted.
2. The generator samples an interior reference cell so each instance has exactly six adjacent cells.
3. Annotation is the set of pixel-space centers for neighboring cells that match the requested state; an empty annotation list is valid when the answer is `0`.
