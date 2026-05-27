# `task_puzzles__cell_board__path_distance`

Status: active default cell-board puzzle task pending fresh merged calibration.

## Identity
1. Domain: `puzzles`
2. Task group: `cell_board`
3. Scene id: `cell_board`
4. Public query variant: `default`
5. Query ids: `shortest_path`, `min_distance`

## Contract
1. Objective: answer one path-distance query on a rectangular tile board.
2. Query branches:
   - `shortest_path`: count steps in the shortest path between two marked cells.
   - `min_distance`: count the minimum orthogonal distance between two queried tile-color sets.
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_sequence`
5. Evidence contains tile-center pixel points along the witness path in path order.

## Notes
1. Movement-style layouts use square cells to keep path length visually uniform.
2. `shortest_path` delegates to the internal tile path generator.
3. `min_distance` delegates to the internal tile relation generator and avoids ties or ambiguous nearest pairs by construction.
4. Internal trace metadata keeps the selected branch in `query_id` and `internal_query_variant`.
