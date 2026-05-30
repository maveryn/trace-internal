# `task_puzzles__cell_board__attribute_count`

Status: active default cell-board puzzle task.

## Identity
1. Domain: `puzzles`
2. Task group: `cell_board`
3. Scene id: `cell_board`
4. Public query id: `default`
5. Query ids: `color_cell_count`, `row_color_cell_count`, `column_color_cell_count`, `edge_color_cell_count`

## Contract
1. Objective: count matching color cells on the whole board, inside one row, inside one column, or on the outer board edge.
2. Implementation/config/prompt source: `puzzles/cell_board_count`
3. Prompt bundle: `puzzles_cell_board_count_v0`
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `point_set`
6. Evidence contains tile-center pixel points for every counted matching cell, or an empty list when the answer is zero.

## Notes
1. Board coordinates remain private verifier metadata.
2. The selected semantic branch is recorded in `query_id`.
3. Answers and evidence come from the same sampled color board and rendered cell-center map.
4. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
5. Render metadata records the sampled shared panel style, coordinate-label font, and scene-local `cell_board.tile_style`.
