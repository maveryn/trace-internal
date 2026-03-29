# `task_puzzles_logic_grid_completion_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles_logic_grid_completion_label`
4. V1 goal: choose the labeled image option that correctly fills one question-mark cell in a shape-logic grid.

## Task variants
1. `row_uniqueness`
   - Each row should contain each visible symbol exactly once.
2. `column_uniqueness`
   - Each column should contain each visible symbol exactly once.
3. `row_and_column_uniqueness`
   - Each row and each column should contain each visible symbol exactly once.

## Scene variants
1. `logic_strip`
2. `logic_card`
3. `logic_outline`

## Contracts
1. Answer type: `answer_gt.type = option_letter`
2. Evidence type: `evidence_gt.type = bbox_set`
3. Evidence cardinality: exactly one bbox
4. Evidence target: the winning option panel bbox

## Scene contract
1. One square logic grid per image.
2. Board size ranges from `3x3` through `5x5`.
3. Exactly one board cell shows `?`.
4. Board cells contain symbolic shapes, not text labels.
5. Exactly six labeled image options (`A` through `F`) appear below the board.
6. Each option panel contains one candidate shape.
7. The prompt asks for the correct option letter, not the shape name.

## Trace contract
1. `scene_ir.entities` includes:
   - `puzzle_logic_cell`
   - `puzzle_logic_option_panel`
   - `puzzle_logic_option_label`
   - `puzzle_logic_option_symbol_box`
2. `render_map.cell_bboxes_px` stores every board-cell bbox keyed by `cell_id`.
3. `render_map.option_panel_bboxes_px` stores every option-panel bbox keyed by `option_panel_id`.
4. `execution_trace` stores:
   - `board_values`
   - `grid_rows`
   - `symbol_pool`
   - `query_cell_id`
   - `query_row_index`
   - `query_col_index`
   - `answer_object_type`
   - `answer_option_label`
   - `correct_option_index`
   - `correct_option_panel_id`
   - `option_specs`
   - `board_size`
   - `board_size_range`
   - `cell_count`
   - `cell_count_range`
   - `option_count`
   - `solver_trace`
5. Prompt-facing evidence is projected from `correct_option_panel_id`, not from pixels.

## Notes
1. V1 keeps the rule family local and explicit: the board rule changes by `task_variant`, but the user interaction stays stable across all instances.
2. The answer space stays healthy because the correct panel rotates across `A..F` deterministically.
