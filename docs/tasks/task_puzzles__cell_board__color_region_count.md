# `task_puzzles__cell_board__color_region_count`

Status: accepted active default cell-board puzzle task.

## Identity
1. Domain: `puzzles`
2. Task group: `cell_board`
3. Scene id: `cell_board`
4. Public query id: `default`
5. Query ids: `color_components`, `largest_component_size`

## Contract
1. Objective: answer one queried-color region metric: 4-neighbor connected-component count or largest 4-neighbor component size.
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `point_set`
4. Evidence contains tile-center pixel points for the counted color cells or the selected largest component.

## Notes
1. Board coordinates remain private verifier metadata.
2. Internal trace metadata keeps the selected source branch in `internal_query_id`.
3. The selected semantic branch is recorded in `query_id`.
4. Render metadata records the sampled shared panel style, coordinate-label font, and scene-local `cell_board.tile_style`.
