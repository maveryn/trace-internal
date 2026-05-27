# `task_puzzles__cell_board__reachability_count`

Status: accepted active default cell-board puzzle task.

## Identity
1. Domain: `puzzles`
2. Task group: `cell_board`
3. Scene id: `cell_board`
4. Public query id: `default`
5. Query ids: `region_size`, `reachable_target_count`, `unreachable_target_count`

## Contract
1. Objective: answer one 4-neighbor reachability count from a marked start tile through non-obstacle tiles.
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `point_set`
4. Evidence contains tile-center pixel points for the reachable region, reachable target tiles, or unreachable target tiles, depending on `query_id`.

## Notes
1. Movement-style layouts use square cells to keep reachability cues visually uniform.
2. Internal trace metadata keeps the selected source branch in `internal_query_id`.
3. The selected semantic branch is recorded in `query_id`.
