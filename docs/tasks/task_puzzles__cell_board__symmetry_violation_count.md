# `task_puzzles__cell_board__symmetry_violation_count`

Status: accepted active default cell-board puzzle task.

## Identity
1. Domain: `puzzles`
2. Task group: `cell_board`
3. Scene id: `cell_board`
4. Public query id: `default`
5. Query id: `symmetry_violation_count`

## Contract
1. Objective: count cells that violate the board's mirror-symmetry rule.
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `point_set`
4. Evidence contains tile-center pixel points for violating cells.

## Notes
1. Symmetry axes and paired cells are recorded in private trace metadata.
2. Internal trace metadata keeps `internal_query_id=symmetry_violation_count`.
3. Render metadata records the sampled shared panel style, coordinate-label font, and scene-local `cell_board.tile_style`.
