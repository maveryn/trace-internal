# `task_puzzles__cell_board__scoped_attribute_count`

## Program Contract
`count_cells(cell_board, predicate=color_equals_query_color, scope=row|column|edge); scene=cell_board; scope=scoped_attribute_count`

## 2) Scene + task contract
1. Entities/relations: A rectangular colored cell board, with row/column labels when needed.
2. Supported `query_id` values: `row_color_cell_count`, `column_color_cell_count`, `edge_color_cell_count`
3. `answer_gt.type`: `integer`
4. Annotation schema: `bbox_set`
5. Alternate annotation forms: none
6. Annotation witness policy: one image-pixel cell bbox for each counted query-color cell inside the requested scope; [] when the answer is 0.
7. Overlap/touch policy: cells outside the requested row, column, or board edge are not annotation witnesses even if their color matches.

## 3) Prompt contract
1. `prompt_bundle_id`: `puzzles_cell_board_v1`
2. `scene_key`: `cell_board`
3. `task_key`: `cell_board_count_query`
4. Prompt query keys match the public `query_id` values.
5. Required slots: `query_color`; `query_row` for row queries; `query_col` for column queries.
6. JSON example validity rule: bbox-set cardinality equals the integer answer for the selected scope.
7. Output modes: `answer_only`, `answer_and_annotation`

## 4) Determinism + constraints
1. Seed namespaces used: task-local scope/color namespaces plus shared cell-board layout/style/font/noise namespaces.
2. Unique-answer policy: construction fixes the count inside the selected scope and records any same-color cells outside the scope as distractors.
3. Reject/resample conditions: impossible scoped answer support raises and retries.
4. No-auto-relaxation guarantee: semantic constraints are not relaxed.
