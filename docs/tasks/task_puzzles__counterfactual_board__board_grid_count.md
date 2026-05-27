# `task_puzzles__counterfactual_board__board_grid_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `counterfactual_board`
3. Task group: `counterfactual`
4. Task id: `task_puzzles__counterfactual_board__board_grid_count`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id` is one of:
   - `row_count`
   - `column_count`
   - `horizontal_line_count`
   - `vertical_line_count`
3. Prompt asks for a visible board/grid count without naming the underlying game or puzzle.
4. Board styles:
   - `chess_checkers`: canonical prior `8 x 8`, sampled visible rows/columns `6..10`
   - `sudoku`: canonical prior `9 x 9`, sampled visible rows/columns `7..11`
   - `xiangqi`: canonical prior `10` horizontal lines by `9` vertical lines, sampled horizontal lines `8..12` and vertical lines `7..11`
5. Cell-board styles use row/column count queries. Xiangqi-style boards use horizontal/vertical line-count queries.
6. Renderings include sparse non-target board contents (checker/chess discs, sudoku givens, and xiangqi-style pieces) to strengthen the familiar board identity; these are decorative and are not counted.
7. Background color is sampled from the shared puzzle-domain light background styles. Board geometry, board colors, and counted-unit projections do not depend on the sampled background.

## Answer And Evidence
1. `answer_gt.type = integer`
2. `answer_gt.value` is the requested visible row, column, horizontal-line, or vertical-line count.
3. `evidence_gt.type = bbox_set`
4. Evidence contains one bbox: the full visible board.

## Trace Contract
1. `scene_ir.entities` includes one `counterfactual_board` entity and private counted row/column/cell/line entities.
2. `execution_trace.board_style`, `visible_rows`, `visible_columns`, `canonical_rows`, and `canonical_columns` record the counterfactual setup.
3. `execution_trace.counted_element_ids` and `counted_element_bboxes_px` record the verifier-side counted units.
4. `execution_trace.canonical_bias_answer` records the answer implied by the canonical board prior.
5. `execution_trace.decorative_item_ids` and `decorative_item_bboxes_px` record the non-target filler digits/pieces separately from counted elements.
6. `render_spec.background_style` records the sampled non-semantic background style.

## Prompt Contract
1. Bundle: `puzzles_counterfactual_v0`
2. Scene key: `counterfactual_board`
3. Task key: `board_grid_count_query`
4. Query key: selected `query_id`
5. Prompt text must not name chess, checkers, sudoku, or xiangqi; the recognizable board prior should come from the image.
