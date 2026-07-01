# Prompt Concision Audit

- rendered prompts: `130`
- tasks covered: `60`
- observed query ids covered: `65`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_puzzles__arithmetic_panel__equal_sum_line_constraint_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__arithmetic_panel__number_wall_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__arithmetic_panel__operation_table_cell_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__arithmetic_panel__row_column_total_missing_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value | `hidden_addition_digit_value, hidden_subtraction_digit_value` | `{'hidden_addition_digit_value': 1, 'hidden_subtraction_digit_value': 1}` | 2 | `` |
| task_puzzles__balance_scale__equivalent_object_count_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__balance_scale__missing_object_weight_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__balance_scale__query_side_relation_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__balance_scale__weight_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cell_board__largest_component_size | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cell_board__reachable_region_size | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cell_board__shortest_path_length_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cell_board__symmetry_violation_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__color_gradient__color_gradient_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__color_gradient__color_gradient_violation_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cube_net__equivalent_net_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cube_net__marked_edge_neighbor_face_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cube_net__opposite_face_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cyclic_order__cyclic_order_equivalent_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cyclic_order__insertion_position_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__cyclic_order__swap_repair_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__matchstick__equation_repair_stick_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__matchstick__matchstick_number_transform_label | `add_one_stick, remove_one_stick` | `{'add_one_stick': 1, 'remove_one_stick': 1}` | 2 | `` |
| task_puzzles__matchstick__max_square_count_after_additions_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__maze__exit_reachability_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__maze__nearest_exit_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__nonogram__candidate_solution_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__nonogram__line_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__pipe_flow__misrotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__pipe_flow__pipe_flow_repair_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__polyomino_assembly__composition_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__polyomino_assembly__decomposition_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_analogical_transform_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_count_progression_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_feature_binding_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_position_progression_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_set_operation_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__raven_matrix__raven_spatial_transform_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__rubiks_net__post_move_face_color_count_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__rubiks_net__post_move_sticker_color_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__rubiks_net__rubiks_move_result_label | `direct_sequence_result_label, inverse_sequence_result_label` | `{'direct_sequence_result_label': 1, 'inverse_sequence_result_label': 1}` | 2 | `` |
| task_puzzles__sheet_transform__fold_cut_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__sheet_transform__fold_projection_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__sheet_transform__overlay_union_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__star_battle__remaining_valid_cell_count | `remaining_valid_cells_in_marked_column_count, remaining_valid_cells_in_marked_region_count, remaining_valid_cells_in_marked_row_count` | `{'remaining_valid_cells_in_marked_column_count': 1, 'remaining_valid_cells_in_marked_region_count': 1, 'remaining_valid_cells_in_marked_row_count': 1}` | 3 | `` |
| task_puzzles__star_battle__valid_cell_anywhere_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__sudoku__marked_cell_candidate_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__sudoku__marked_cell_value | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__sudoku__mistake_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__tents__missing_tent_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__tents__violating_tent_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__toggle_grid__toggle_repair_switch_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__toggle_grid__toggle_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_painted_face_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_projection_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_structure_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_visible_projection_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__word_search__present_word_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__word_search__search_location_label | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_puzzles__cell_board__shortest_path_length_value / answer_and_annotation / sample 731097966873527

- `query_id`: `single`
- `instance_seed`: `731097966873527`
- `word_count`: `103`
- `body_word_count`: `103`

```text
The image shows a board of colored square or rectangular cells. For any path, reachability, or component question, use only up, down, left, and right steps. How many orthogonal steps are in the shortest path from S to G without crossing dark wall cells?
Set answer to the shortest path length in orthogonal cell steps.
Set annotation to a segment_set: one image-pixel segment [[x1,y1],[x2,y2]] for each adjacent step along a shortest S-to-G path.
Use this JSON shape for the final response: {"annotation":[[[100,100],[136,100]],[[136,100],[136,136]],[[136,136],[172,136]],[[172,136],[172,172]]],"answer":4}.
```

### task_puzzles__star_battle__remaining_valid_cell_count / answer_and_annotation / sample 2869593182357784

- `query_id`: `remaining_valid_cells_in_marked_column_count`
- `instance_seed`: `2869593182357784`
- `word_count`: `103`
- `body_word_count`: `90`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Use the visible stars and the Star Battle rules: one star in each row, column, and colored region, and no two stars touching. How many possible star placements remain in the marked column?
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked column; answer should be the count of legal star cells in the marked column.
Example JSON:
{"annotation":[[402,276,466,340],[402,468,466,532]],"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / answer_and_annotation / sample 4468537011817492

- `query_id`: `remaining_valid_cells_in_marked_region_count`
- `instance_seed`: `4468537011817492`
- `word_count`: `103`
- `body_word_count`: `90`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Apply the Star Battle rules: one star per row, column, and colored region; stars cannot touch by edge or corner. Within the marked region, count every cell where another star could be placed.
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked region; answer should be the count of legal star cells in the marked region.
Example JSON:
{"annotation":[[402,276,466,340],[466,340,530,404]],"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / answer_and_annotation / sample 6297137922527172

- `query_id`: `remaining_valid_cells_in_marked_row_count`
- `instance_seed`: `6297137922527172`
- `word_count`: `102`
- `body_word_count`: `89`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. In Star Battle, every row, column, and colored region needs exactly one star, and no two stars may touch, even diagonally. Count the legal remaining star cells inside the marked row.
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked row; answer should be the count of legal star cells in the marked row.
Example JSON:
{"annotation":[[402,276,466,340],[530,276,594,340]],"answer":2}
```

### task_puzzles__pipe_flow__pipe_flow_repair_tile_label / answer_and_annotation / sample 277694648037652

- `query_id`: `single`
- `instance_seed`: `277694648037652`
- `word_count`: `100`
- `body_word_count`: `85`

```text
The figure shows a pipe-tile grid with a green start marker and a red triangular finish flag. Which labeled 2x2 repair piece fits the missing black region as shown and restores flow from the green start marker to the red finish flag?
Set answer to the selected repair option letter as a string.
Set annotation to an object with keys "selected_option" and "missing_gap". Each value is one image-pixel bounding box [x0,y0,x1,y1] around that visual witness.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":{"selected_option":[774,248,902,376],"missing_gap":[424,312,512,400]},"answer":"C"}
```

### task_puzzles__cell_board__symmetry_violation_count / answer_and_annotation / sample 4188294073177469

- `query_id`: `single`
- `instance_seed`: `4188294073177469`
- `word_count`: `95`
- `body_word_count`: `95`

```text
The image shows a cell board with one colored tile in each grid position. Use the stated mirror axis and count only the requested side. Using the horizontal mirror axis, how many cells on the top side do not match their mirror cell?
Set answer to the number of counted-side cells that fail the mirror check.
Set annotation to a segment_set: one image-pixel segment [[x1,y1],[x2,y2]] from each counted-side violating cell center to its mirror-cell center.
Write only a JSON object like {"annotation":[[[118,118],[214,118]],[[118,166],[214,166]]],"answer":2}.
```

### task_puzzles__pipe_flow__misrotated_tile_label / answer_and_annotation / sample 7765548981679743

- `query_id`: `single`
- `instance_seed`: `7765548981679743`
- `word_count`: `94`
- `body_word_count`: `85`

```text
The image shows a circuit-trace tile grid with a green start marker and a red triangular finish flag. One labeled pipe tile is rotated away from its correct orientation. Which label marks the tile that should be rotated to restore the path from the green start marker to the red finish flag?
Set answer to the selected tile letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the tile that should be rotated.
Return both fields in JSON.
Example JSON:
{"annotation":[376,248,420,286],"answer":"B"}
```

### task_puzzles__cell_board__reachable_region_size / answer_and_annotation / sample 3417660624961556

- `query_id`: `single`
- `instance_seed`: `3417660624961556`
- `word_count`: `93`
- `body_word_count`: `93`

```text
The image shows a rectangular tile grid. When checking connected regions or movement, count orthogonal cell steps only. Using side-adjacent moves from S, count the reachable passable cells; dark cells are walls and S is included.
Set answer to the number of light passable cells reachable from S by side-adjacent moves, including S.
Set annotation to a bbox_set containing the image-pixel cell boxes for all reachable passable cells, including S.
Use this JSON shape for the final response: {"annotation":[[100,100,136,136],[148,100,184,136],[148,148,184,184]],"answer":3}.
```

### task_puzzles__balance_scale__query_side_relation_label / answer_and_annotation / sample 1801053817413268

- `query_id`: `single`
- `instance_seed`: `1801053817413268`
- `word_count`: `92`
- `body_word_count`: `50`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. Each reference scale is balanced. For the query comparison, choose whether the left side is heavier, the right side is heavier, the two sides balance, or the relation cannot be determined.
Annotation format: set "annotation" to the image-pixel bounding box [x0, y0, x1, y1] around the selected option.
Answer format: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[720,650,920,710],"answer":"D"}
```

### task_puzzles__balance_scale__weight_order_label / answer_and_annotation / sample 6921560432896808

- `query_id`: `single`
- `instance_seed`: `6921560432896808`
- `word_count`: `92`
- `body_word_count`: `37`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. The lower pan is heavier and a level scale means equal weight. Which option shows the correct order?
Annotation format: set "annotation" to a JSON array of three image-pixel bounding boxes [x0, y0, x1, y1], one for each comparison scale.
Answer format: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[[80,92,1040,260],[80,284,1040,452],[80,476,1040,644]],"answer":"C"}
```

### task_puzzles__tents__missing_tent_cell_label / answer_and_annotation / sample 7739839479435094

- `query_id`: `single`
- `instance_seed`: `7739839479435094`
- `word_count`: `92`
- `body_word_count`: `83`

```text
The image shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. Find the only labeled candidate cell where the marked tree's missing tent can be placed while satisfying the clues and no-touch rule.
Set answer to the label of the only candidate cell where the marked tree's missing tent can be placed.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the selected candidate cell.
Return both fields in JSON.
Example JSON:
{"annotation":[512,386,574,448],"answer":"C"}
```

### task_puzzles__tents__violating_tent_label / answer_and_annotation / sample 1869727188121144

- `query_id`: `single`
- `instance_seed`: `1869727188121144`
- `word_count`: `92`
- `body_word_count`: `83`

```text
The figure shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. A tent must be directly above, below, left, or right of a tree. Which labeled tent is not next to any tree?
Set answer to the label of the tent that is not orthogonally adjacent to any tree.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the selected labeled tent cell.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[356,226,416,286],"answer":"B"}
```

### task_puzzles__rubiks_net__post_move_face_color_count_label / answer_and_annotation / sample 240126542032281

- `query_id`: `single`
- `instance_seed`: `240126542032281`
- `word_count`: `90`
- `body_word_count`: `81`

```text
The scene shows a Rubik-style cube net with face labels, a Target color swatch, and four labeled number options; a prime mark means counterclockwise as viewed from outside the turned face. Use moves U'; which number option counts stickers matching the Target color on the Left face?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected option panel.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[836,492,972,646],"answer":"A"}
```

### task_puzzles__rubiks_net__post_move_sticker_color_label / answer_and_annotation / sample 6658997801619891

- `query_id`: `single`
- `instance_seed`: `6658997801619891`
- `word_count`: `90`
- `body_word_count`: `81`

```text
The visual shows a Rubik-style cube net with face labels, a (column,row) coordinate reference, and four labeled color-swatch options; a prime mark means counterclockwise as viewed from outside the turned face. Choose the swatch for position (2, 2) on the Right face after applying U F.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected option panel.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[990,126,1126,280],"answer":"C"}
```

### task_puzzles__word_search__search_location_label / answer_and_annotation / sample 655130434197869

- `query_id`: `single`
- `instance_seed`: `655130434197869`
- `word_count`: `89`
- `body_word_count`: `72`

```text
The word-search puzzle shows a row-and-column labeled word-search grid. Use the grid labels to locate "ABLE". Which option lists the correct start row, start column, and direction?
Set answer to the selected option letter.
Set annotation to a JSON array of ordered image-pixel bounding boxes [x0,y0,x1,y1], one for each grid cell in the found word from first letter to last letter.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[[194,222,252,280],[252,222,310,280],[310,222,368,280]],"answer":"C"}
```

### task_puzzles__toggle_grid__toggle_result_label / answer_and_annotation / sample 8623333450752672

- `query_id`: `single`
- `instance_seed`: `8623333450752672`
- `word_count`: `87`
- `body_word_count`: `78`

```text
The figure shows a notebook-style toggle grid with switch cells, binary cell states, and visual answer options. Apply the visible red switch press to the start grid using the orthogonal-neighbor toggle rule. Which labeled result grid is produced?
Set answer to the label of the result-grid option produced by pressing the red marked switch.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected result option panel.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[722,552,882,806],"answer":"D"}
```

### task_puzzles__cyclic_order__swap_repair_label / answer_and_annotation / sample 4898275474869701

- `query_id`: `single`
- `instance_seed`: `4898275474869701`
- `word_count`: `86`
- `body_word_count`: `77`

```text
The figure shows a reference charm loop, a broken numbered loop, and six swap options. Use the token colors when comparing cyclic order. Select the only swap option that repairs the broken loop into a rotated copy of the reference order.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] around the selected swap option card.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[493,425,707,521],"answer":"C"}
```

### task_puzzles__matchstick__max_square_count_after_additions_value / answer_and_annotation / sample 1369794825561587

- `query_id`: `single`
- `instance_seed`: `1369794825561587`
- `word_count`: `85`
- `body_word_count`: `85`

```text
The puzzle diagram shows a matchstick square lattice with some empty grid edges. Place exactly 1 more matchsticks on empty grid edges. How many complete unit squares can there be at most?
Set answer to the maximum number of complete unit squares that can be present.
Set annotation to a bbox_set in image pixels, one bounding box [x0, y0, x1, y1] for each complete unit square counted in the final board.
Return JSON like {"annotation":[[126,118,226,218],[226,118,326,218]],"answer":2}.
```

### task_puzzles__cell_board__largest_component_size / answer_and_annotation / sample 6505061166212726

- `query_id`: `single`
- `instance_seed`: `6505061166212726`
- `word_count`: `84`
- `body_word_count`: `84`

```text
The image shows a cell board with one colored tile in each grid position. Use the board cells exactly as drawn; only edge-sharing cells are adjacent. Count the cells in the largest connected group of yellow cells.
Set answer to the number of cells in the largest target-color component.
Set annotation to a bbox_set containing the image-pixel cell boxes in that largest connected component.
Return both fields in JSON: {"annotation":[[100,100,136,136],[148,100,184,136],[148,148,184,184]],"answer":3}.
```

### task_puzzles__cyclic_order__insertion_position_label / answer_and_annotation / sample 6492238051144079

- `query_id`: `single`
- `instance_seed`: `6492238051144079`
- `word_count`: `84`
- `body_word_count`: `75`

```text
The puzzle diagram shows a reference route loop and a partial loop with labeled gaps. Use the token colors when comparing cyclic order. One token from the reference is absent from the partial loop. Which labeled gap restores the reference cyclic order?
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] around the selected labeled gap badge.
Return both fields in JSON.
Example JSON:
{"annotation":[755,231,793,269],"answer":"C"}
```

### task_puzzles__matchstick__matchstick_number_transform_label / answer_and_annotation / sample 2862873540596054

- `query_id`: `remove_one_stick`
- `instance_seed`: `2862873540596054`
- `word_count`: `84`
- `body_word_count`: `84`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by removing exactly one stick from the Source.
Set answer to the single option label as a capital letter.
Set annotation to a bbox_map in image pixels with keys source_number and selected_option. Each key maps to one bounding box [x0, y0, x1, y1].
Use this JSON shape for the final response: {"annotation":{"source_number":[58,58,1142,288],"selected_option":[440,332,760,550]},"answer":"B"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / answer_and_annotation / sample 8775820870254963

- `query_id`: `add_one_stick`
- `instance_seed`: `8775820870254963`
- `word_count`: `83`
- `body_word_count`: `83`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by adding exactly one stick to the Source.
Set answer to the single option label as a capital letter.
Set annotation to a bbox_map in image pixels with keys source_number and selected_option. Each key maps to one bounding box [x0, y0, x1, y1].
Use the answer-and-annotation JSON shape shown here: {"annotation":{"source_number":[58,58,1142,288],"selected_option":[440,332,760,550]},"answer":"B"}.
```

### task_puzzles__voxel_cube__cube_structure_change_count / answer_and_annotation / sample 7764713121168464

- `query_id`: `single`
- `instance_seed`: `7764713121168464`
- `word_count`: `81`
- `body_word_count`: `68`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. The reference shows the complete cuboid. How many cubes are absent from the changed version?
Set answer to the number of cubes that must be added as an integer.
Set annotation to a JSON array of image-pixel bounding boxes [x0,y0,x1,y1], one around each compared structure.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[[120,210,420,560],[520,225,820,560]],"answer":2}
```

### task_puzzles__raven_matrix__raven_feature_binding_label / answer_and_annotation / sample 7303803524000724

- `query_id`: `single`
- `instance_seed`: `7303803524000724`
- `word_count`: `80`
- `body_word_count`: `71`

```text
The image shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Use how two visual properties vary systematically across the matrix to choose the option that completes the missing lower-right cell.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[629,647,735,752],"answer":"C"}
```

### task_puzzles__star_battle__valid_cell_anywhere_label / answer_and_annotation / sample 892184768993533

- `query_id`: `single`
- `instance_seed`: `892184768993533`
- `word_count`: `80`
- `body_word_count`: `71`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and labeled candidate cells. Use these Star Battle rules: each row, column, and colored region must contain exactly one star; stars cannot touch, even diagonally. Which candidate label marks a legal remaining star cell?
Return annotation as [x0,y0,x1,y1], the image-pixel bbox of the selected candidate cell and answer as the legal candidate letter.
Example JSON:
{"annotation":[402,276,466,340],"answer":"C"}
```

## Repeated Scaffolding Terms

### task_puzzles__toggle_grid__toggle_result_label / answer_and_annotation / sample 8623333450752672

- `query_id`: `single`
- `instance_seed`: `8623333450752672`
- `word_count`: `87`
- `body_word_count`: `78`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows a notebook-style toggle grid with switch cells, binary cell states, and visual answer options. Apply the visible red switch press to the start grid using the orthogonal-neighbor toggle rule. Which labeled result grid is produced?
Set answer to the label of the result-grid option produced by pressing the red marked switch.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected result option panel.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[722,552,882,806],"answer":"D"}
```

### task_puzzles__matchstick__matchstick_number_transform_label / answer_and_annotation / sample 8775820870254963

- `query_id`: `add_one_stick`
- `instance_seed`: `8775820870254963`
- `word_count`: `83`
- `body_word_count`: `83`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by adding exactly one stick to the Source.
Set answer to the single option label as a capital letter.
Set annotation to a bbox_map in image pixels with keys source_number and selected_option. Each key maps to one bounding box [x0, y0, x1, y1].
Use the answer-and-annotation JSON shape shown here: {"annotation":{"source_number":[58,58,1142,288],"selected_option":[440,332,760,550]},"answer":"B"}.
```

### task_puzzles__raven_matrix__raven_feature_binding_label / answer_and_annotation / sample 7303803524000724

- `query_id`: `single`
- `instance_seed`: `7303803524000724`
- `word_count`: `80`
- `body_word_count`: `71`
- `repeated_terms`: `{'image': 3}`

```text
The image shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Use how two visual properties vary systematically across the matrix to choose the option that completes the missing lower-right cell.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[629,647,735,752],"answer":"C"}
```

### task_puzzles__cube_net__marked_edge_neighbor_face_label / answer_and_annotation / sample 97416272057205

- `query_id`: `single`
- `instance_seed`: `97416272057205`
- `word_count`: `70`
- `body_word_count`: `70`
- `repeated_terms`: `{'answer': 3}`

```text
The puzzle diagram shows a labeled cube net with one red marked edge and labeled face options. Which labeled option touches the red marked edge on the folded cube?
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option card.
Use the answer-and-annotation JSON shape shown here: {"annotation":[812,220,966,326],"answer":"D"}.
```

### task_puzzles__cell_board__shortest_path_length_value / answer_only / sample 731097966873527

- `query_id`: `single`
- `instance_seed`: `731097966873527`
- `word_count`: `64`
- `body_word_count`: `64`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a board of colored square or rectangular cells. For any path, reachability, or component question, use only up, down, left, and right steps. How many orthogonal steps are in the shortest path from S to G without crossing dark wall cells?
Set answer to the shortest path length in orthogonal cell steps.
Use the answer-only JSON shape shown here: {"answer":4}.
```

### task_puzzles__cell_board__symmetry_violation_count / answer_only / sample 4188294073177469

- `query_id`: `single`
- `instance_seed`: `4188294073177469`
- `word_count`: `64`
- `body_word_count`: `64`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a cell board with one colored tile in each grid position. Use the stated mirror axis and count only the requested side. Using the horizontal mirror axis, how many cells on the top side do not match their mirror cell?
Set answer to the number of counted-side cells that fail the mirror check.
Return the integer answer in JSON: {"answer":2}.
```

### task_puzzles__cube_net__equivalent_net_label / answer_only / sample 32405557239426

- `query_id`: `single`
- `instance_seed`: `32405557239426`
- `word_count`: `55`
- `body_word_count`: `55`
- `repeated_terms`: `{'answer': 3}`

```text
This puzzle diagram shows a reference colored cube net and four labeled candidate colored cube nets. Choose the candidate net that makes the same colored cube as the reference after folding and turning the cube.
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__cube_net__marked_edge_neighbor_face_label / answer_only / sample 97416272057205

- `query_id`: `single`
- `instance_seed`: `97416272057205`
- `word_count`: `49`
- `body_word_count`: `49`
- `repeated_terms`: `{'answer': 3}`

```text
The puzzle diagram shows a labeled cube net with one red marked edge and labeled face options. Which labeled option touches the red marked edge on the folded cube?
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__cube_net__opposite_face_label / answer_only / sample 6144008333654395

- `query_id`: `single`
- `instance_seed`: `6144008333654395`
- `word_count`: `47`
- `body_word_count`: `47`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a labeled cube net with one marked reference face and labeled face options. Choose the option for the face opposite the marked reference face.
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / answer_only / sample 8775820870254963

- `query_id`: `add_one_stick`
- `instance_seed`: `8775820870254963`
- `word_count`: `46`
- `body_word_count`: `46`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by adding exactly one stick to the Source.
Set answer to the single option label as a capital letter.
Return the answer in JSON: {"answer":"B"}.
```

### task_puzzles__matchstick__equation_repair_stick_label / answer_only / sample 8090816052123110

- `query_id`: `single`
- `instance_seed`: `8090816052123110`
- `word_count`: `42`
- `body_word_count`: `42`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows a false matchstick equation with labeled digit sticks. Remove exactly one labeled stick. Which label makes the equation true?
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"B"}.
```

## All Prompt Samples

### task_puzzles__arithmetic_panel__equal_sum_line_constraint_value / single / answer_and_annotation / sample 6456016301975454

- `instance_seed`: `6456016301975454`
- `word_count`: `59`
- `body_word_count`: `18`

```text
This display shows a number puzzle diagram with one question-mark entry. What integer belongs in the question-mark node?
Required annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark node.
Required answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"annotation":[546,470,622,546],"answer":8}
```

### task_puzzles__arithmetic_panel__equal_sum_line_constraint_value / single / answer_only / sample 6456016301975454

- `instance_seed`: `6456016301975454`
- `word_count`: `34`
- `body_word_count`: `18`

```text
This display shows a number puzzle diagram with one question-mark entry. What integer belongs in the question-mark node?
Answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"answer":8}
```

### task_puzzles__arithmetic_panel__number_wall_value / single / answer_and_annotation / sample 6269201095371080

- `instance_seed`: `6269201095371080`
- `word_count`: `58`
- `body_word_count`: `19`

```text
The figure shows a number puzzle diagram with one question-mark entry. Find the hidden number in the number wall.
Annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark brick.
Answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"annotation":[498,416,600,488],"answer":9}
```

### task_puzzles__arithmetic_panel__number_wall_value / single / answer_only / sample 6269201095371080

- `instance_seed`: `6269201095371080`
- `word_count`: `36`
- `body_word_count`: `19`

```text
The figure shows a number puzzle diagram with one question-mark entry. Find the hidden number in the number wall.
Required answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"answer":9}
```

### task_puzzles__arithmetic_panel__operation_table_cell_value / single / answer_and_annotation / sample 255606288692337

- `instance_seed`: `255606288692337`
- `word_count`: `64`
- `body_word_count`: `24`

```text
The visual shows a number puzzle diagram with one question-mark entry. Use the visible headers and corner symbol to complete the marked table cell.
Annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark table cell.
Answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"annotation":[582,404,666,476],"answer":15}
```

### task_puzzles__arithmetic_panel__operation_table_cell_value / single / answer_only / sample 255606288692337

- `instance_seed`: `255606288692337`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The visual shows a number puzzle diagram with one question-mark entry. Use the visible headers and corner symbol to complete the marked table cell.
Answer field: set "answer" to the integer that replaces the question mark.
Example JSON:
{"answer":15}
```

### task_puzzles__arithmetic_panel__row_column_total_missing_value / single / answer_and_annotation / sample 5016234363269078

- `instance_seed`: `5016234363269078`
- `word_count`: `60`
- `body_word_count`: `20`

```text
The figure shows a number puzzle diagram with one question-mark entry. Solve the marked grid cell from the displayed clues.
Annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark grid cell.
Answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"annotation":[498,332,582,404],"answer":8}
```

### task_puzzles__arithmetic_panel__row_column_total_missing_value / single / answer_only / sample 5016234363269078

- `instance_seed`: `5016234363269078`
- `word_count`: `37`
- `body_word_count`: `20`

```text
The figure shows a number puzzle diagram with one question-mark entry. Solve the marked grid cell from the displayed clues.
Final answer format: set "answer" to the integer that replaces the question mark.
Example JSON:
{"answer":8}
```

### task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value / hidden_addition_digit_value / answer_and_annotation / sample 7164332989709397

- `instance_seed`: `7164332989709397`
- `word_count`: `61`
- `body_word_count`: `19`

```text
The image shows a number puzzle diagram with one question-mark entry. Find the digit that completes the marked cell.
Required annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark digit cell.
Required answer format: set "answer" to the digit that replaces the question mark.
Example JSON:
{"annotation":[560,302,644,374],"answer":7}
```

### task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value / hidden_addition_digit_value / answer_only / sample 7164332989709397

- `instance_seed`: `7164332989709397`
- `word_count`: `35`
- `body_word_count`: `19`

```text
The image shows a number puzzle diagram with one question-mark entry. Find the digit that completes the marked cell.
Answer format: set "answer" to the digit that replaces the question mark.
Example JSON:
{"answer":7}
```

### task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value / hidden_subtraction_digit_value / answer_and_annotation / sample 6687874497083322

- `instance_seed`: `6687874497083322`
- `word_count`: `61`
- `body_word_count`: `21`

```text
The panel shows a number puzzle diagram with one question-mark entry. Complete the marked digit so the displayed calculation is correct.
Annotation format: set "annotation" to the pixel bounding box [x0, y0, x1, y1] around the marked question-mark digit cell.
Answer format: set "answer" to the digit that replaces the question mark.
Example JSON:
{"annotation":[476,386,560,458],"answer":4}
```

### task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value / hidden_subtraction_digit_value / answer_only / sample 6687874497083322

- `instance_seed`: `6687874497083322`
- `word_count`: `37`
- `body_word_count`: `21`

```text
The panel shows a number puzzle diagram with one question-mark entry. Complete the marked digit so the displayed calculation is correct.
Answer format: set "answer" to the digit that replaces the question mark.
Example JSON:
{"answer":4}
```

### task_puzzles__balance_scale__equivalent_object_count_value / single / answer_and_annotation / sample 5262849741547273

- `instance_seed`: `5262849741547273`
- `word_count`: `79`
- `body_word_count`: `38`

```text
This balance-scale puzzle shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. The query row asks how many repeated objects balance one source object. What integer count replaces the question mark?
Required annotation format: set "annotation" to the image-pixel bounding box [x0, y0, x1, y1] around the question-mark count box.
Required answer format: set "answer" to the integer count in the question-mark box.
Example JSON:
{"annotation":[570,648,628,708],"answer":4}
```

### task_puzzles__balance_scale__equivalent_object_count_value / single / answer_only / sample 5262849741547273

- `instance_seed`: `5262849741547273`
- `word_count`: `57`
- `body_word_count`: `38`

```text
This balance-scale puzzle shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. The query row asks how many repeated objects balance one source object. What integer count replaces the question mark?
Format for the "answer" field: set "answer" to the integer count in the question-mark box.
Example JSON:
{"answer":4}
```

### task_puzzles__balance_scale__missing_object_weight_value / single / answer_and_annotation / sample 3705924834428719

- `instance_seed`: `3705924834428719`
- `word_count`: `76`
- `body_word_count`: `36`

```text
The visual shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. Use the three unknown objects and numbered weights on the balanced scales to find the query object's value.
Final answer format: set "answer" to the integer value of the query object.
Annotation format: set "annotation" to the image-pixel bounding box [x0, y0, x1, y1] around the question-mark value box.
Example JSON:
{"annotation":[630,646,696,712],"answer":8}
```

### task_puzzles__balance_scale__missing_object_weight_value / single / answer_only / sample 3705924834428719

- `instance_seed`: `3705924834428719`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The visual shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. Use the three unknown objects and numbered weights on the balanced scales to find the query object's value.
Required answer format: set "answer" to the integer value of the query object.
Example JSON:
{"answer":8}
```

### task_puzzles__balance_scale__query_side_relation_label / single / answer_and_annotation / sample 1801053817413268

- `instance_seed`: `1801053817413268`
- `word_count`: `92`
- `body_word_count`: `50`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. Each reference scale is balanced. For the query comparison, choose whether the left side is heavier, the right side is heavier, the two sides balance, or the relation cannot be determined.
Annotation format: set "annotation" to the image-pixel bounding box [x0, y0, x1, y1] around the selected option.
Answer format: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[720,650,920,710],"answer":"D"}
```

### task_puzzles__balance_scale__query_side_relation_label / single / answer_only / sample 1801053817413268

- `instance_seed`: `1801053817413268`
- `word_count`: `71`
- `body_word_count`: `50`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. Each reference scale is balanced. For the query comparison, choose whether the left side is heavier, the right side is heavier, the two sides balance, or the relation cannot be determined.
Required answer format: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"D"}
```

### task_puzzles__balance_scale__weight_order_label / single / answer_and_annotation / sample 6921560432896808

- `instance_seed`: `6921560432896808`
- `word_count`: `92`
- `body_word_count`: `37`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. The lower pan is heavier and a level scale means equal weight. Which option shows the correct order?
Annotation format: set "annotation" to a JSON array of three image-pixel bounding boxes [x0, y0, x1, y1], one for each comparison scale.
Answer format: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[[80,92,1040,260],[80,284,1040,452],[80,476,1040,644]],"answer":"C"}
```

### task_puzzles__balance_scale__weight_order_label / single / answer_only / sample 6921560432896808

- `instance_seed`: `6921560432896808`
- `word_count`: `57`
- `body_word_count`: `53`

```text
The puzzle diagram shows three pan-scale comparison panels with three labeled unknown objects, numbered weights, and a query row. The lower pan is heavier and a level scale means equal weight. Which option shows the correct order?
Answer field: set "answer" to the matching option label, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"C"}
```

### task_puzzles__cell_board__largest_component_size / single / answer_and_annotation / sample 6505061166212726

- `instance_seed`: `6505061166212726`
- `word_count`: `84`
- `body_word_count`: `84`

```text
The image shows a cell board with one colored tile in each grid position. Use the board cells exactly as drawn; only edge-sharing cells are adjacent. Count the cells in the largest connected group of yellow cells.
Set answer to the number of cells in the largest target-color component.
Set annotation to a bbox_set containing the image-pixel cell boxes in that largest connected component.
Return both fields in JSON: {"annotation":[[100,100,136,136],[148,100,184,136],[148,148,184,184]],"answer":3}.
```

### task_puzzles__cell_board__largest_component_size / single / answer_only / sample 6505061166212726

- `instance_seed`: `6505061166212726`
- `word_count`: `57`
- `body_word_count`: `57`

```text
The image shows a cell board with one colored tile in each grid position. Use the board cells exactly as drawn; only edge-sharing cells are adjacent. Count the cells in the largest connected group of yellow cells.
Set answer to the number of cells in the largest target-color component.
Write only a JSON object like {"answer":3}.
```

### task_puzzles__cell_board__reachable_region_size / single / answer_and_annotation / sample 3417660624961556

- `instance_seed`: `3417660624961556`
- `word_count`: `93`
- `body_word_count`: `93`

```text
The image shows a rectangular tile grid. When checking connected regions or movement, count orthogonal cell steps only. Using side-adjacent moves from S, count the reachable passable cells; dark cells are walls and S is included.
Set answer to the number of light passable cells reachable from S by side-adjacent moves, including S.
Set annotation to a bbox_set containing the image-pixel cell boxes for all reachable passable cells, including S.
Use this JSON shape for the final response: {"annotation":[[100,100,136,136],[148,100,184,136],[148,148,184,184]],"answer":3}.
```

### task_puzzles__cell_board__reachable_region_size / single / answer_only / sample 3417660624961556

- `instance_seed`: `3417660624961556`
- `word_count`: `58`
- `body_word_count`: `58`

```text
The image shows a rectangular tile grid. When checking connected regions or movement, count orthogonal cell steps only. Using side-adjacent moves from S, count the reachable passable cells; dark cells are walls and S is included.
Set answer to the number of light passable cells reachable from S by side-adjacent moves, including S.
Return JSON like {"answer":3}.
```

### task_puzzles__cell_board__shortest_path_length_value / single / answer_and_annotation / sample 731097966873527

- `instance_seed`: `731097966873527`
- `word_count`: `103`
- `body_word_count`: `103`

```text
The image shows a board of colored square or rectangular cells. For any path, reachability, or component question, use only up, down, left, and right steps. How many orthogonal steps are in the shortest path from S to G without crossing dark wall cells?
Set answer to the shortest path length in orthogonal cell steps.
Set annotation to a segment_set: one image-pixel segment [[x1,y1],[x2,y2]] for each adjacent step along a shortest S-to-G path.
Use this JSON shape for the final response: {"annotation":[[[100,100],[136,100]],[[136,100],[136,136]],[[136,136],[172,136]],[[172,136],[172,172]]],"answer":4}.
```

### task_puzzles__cell_board__shortest_path_length_value / single / answer_only / sample 731097966873527

- `instance_seed`: `731097966873527`
- `word_count`: `64`
- `body_word_count`: `64`

```text
The image shows a board of colored square or rectangular cells. For any path, reachability, or component question, use only up, down, left, and right steps. How many orthogonal steps are in the shortest path from S to G without crossing dark wall cells?
Set answer to the shortest path length in orthogonal cell steps.
Use the answer-only JSON shape shown here: {"answer":4}.
```

### task_puzzles__cell_board__symmetry_violation_count / single / answer_and_annotation / sample 4188294073177469

- `instance_seed`: `4188294073177469`
- `word_count`: `95`
- `body_word_count`: `95`

```text
The image shows a cell board with one colored tile in each grid position. Use the stated mirror axis and count only the requested side. Using the horizontal mirror axis, how many cells on the top side do not match their mirror cell?
Set answer to the number of counted-side cells that fail the mirror check.
Set annotation to a segment_set: one image-pixel segment [[x1,y1],[x2,y2]] from each counted-side violating cell center to its mirror-cell center.
Write only a JSON object like {"annotation":[[[118,118],[214,118]],[[118,166],[214,166]]],"answer":2}.
```

### task_puzzles__cell_board__symmetry_violation_count / single / answer_only / sample 4188294073177469

- `instance_seed`: `4188294073177469`
- `word_count`: `64`
- `body_word_count`: `64`

```text
The image shows a cell board with one colored tile in each grid position. Use the stated mirror axis and count only the requested side. Using the horizontal mirror axis, how many cells on the top side do not match their mirror cell?
Set answer to the number of counted-side cells that fail the mirror check.
Return the integer answer in JSON: {"answer":2}.
```

### task_puzzles__color_gradient__color_gradient_completion_label / single / answer_and_annotation / sample 5305863780643812

- `instance_seed`: `5305863780643812`
- `word_count`: `71`
- `body_word_count`: `62`

```text
The image shows a notebook-style row of color swatches with one blank swatch and labeled color options. Choose the option label whose color fits the blank position in the gradient row.
Set answer to the single capital-letter label of the option that completes the color gradient.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] for the selected option swatch.
Example JSON:
{"annotation":[524,420,628,524],"answer":"C"}
```

### task_puzzles__color_gradient__color_gradient_completion_label / single / answer_only / sample 5305863780643812

- `instance_seed`: `5305863780643812`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The image shows a notebook-style row of color swatches with one blank swatch and labeled color options. Choose the option label whose color fits the blank position in the gradient row.
Set answer to the single capital-letter label of the option that completes the color gradient.
Return the answer in JSON.
Example JSON:
{"answer":"C"}
```

### task_puzzles__color_gradient__color_gradient_violation_cell_label / single / answer_and_annotation / sample 6567354500222237

- `instance_seed`: `6567354500222237`
- `word_count`: `77`
- `body_word_count`: `68`

```text
The diagram shows a card-framed labeled grid of color swatches arranged as a smooth color progression. Use the row and column color changes to find the out-of-pattern swatch. Which label is it?
Set answer to the single capital-letter label of the swatch that breaks the progression.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] for that swatch cell.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[324,188,432,296],"answer":"F"}
```

### task_puzzles__color_gradient__color_gradient_violation_cell_label / single / answer_only / sample 6567354500222237

- `instance_seed`: `6567354500222237`
- `word_count`: `58`
- `body_word_count`: `54`

```text
The diagram shows a card-framed labeled grid of color swatches arranged as a smooth color progression. Use the row and column color changes to find the out-of-pattern swatch. Which label is it?
Set answer to the single capital-letter label of the swatch that breaks the progression.
Write only a JSON object in this shape.
Example JSON:
{"answer":"F"}
```

### task_puzzles__cube_net__equivalent_net_label / single / answer_and_annotation / sample 32405557239426

- `instance_seed`: `32405557239426`
- `word_count`: `75`
- `body_word_count`: `75`

```text
This puzzle diagram shows a reference colored cube net and four labeled candidate colored cube nets. Choose the candidate net that makes the same colored cube as the reference after folding and turning the cube.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option net panel.
Return both fields in JSON: {"annotation":[782,452,1074,774],"answer":"D"}.
```

### task_puzzles__cube_net__equivalent_net_label / single / answer_only / sample 32405557239426

- `instance_seed`: `32405557239426`
- `word_count`: `55`
- `body_word_count`: `55`

```text
This puzzle diagram shows a reference colored cube net and four labeled candidate colored cube nets. Choose the candidate net that makes the same colored cube as the reference after folding and turning the cube.
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__cube_net__marked_edge_neighbor_face_label / single / answer_and_annotation / sample 97416272057205

- `instance_seed`: `97416272057205`
- `word_count`: `70`
- `body_word_count`: `70`

```text
The puzzle diagram shows a labeled cube net with one red marked edge and labeled face options. Which labeled option touches the red marked edge on the folded cube?
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option card.
Use the answer-and-annotation JSON shape shown here: {"annotation":[812,220,966,326],"answer":"D"}.
```

### task_puzzles__cube_net__marked_edge_neighbor_face_label / single / answer_only / sample 97416272057205

- `instance_seed`: `97416272057205`
- `word_count`: `49`
- `body_word_count`: `49`

```text
The puzzle diagram shows a labeled cube net with one red marked edge and labeled face options. Which labeled option touches the red marked edge on the folded cube?
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__cube_net__opposite_face_label / single / answer_and_annotation / sample 6144008333654395

- `instance_seed`: `6144008333654395`
- `word_count`: `64`
- `body_word_count`: `64`

```text
The image shows a labeled cube net with one marked reference face and labeled face options. Choose the option for the face opposite the marked reference face.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option card.
Return JSON like {"annotation":[812,220,966,326],"answer":"D"}.
```

### task_puzzles__cube_net__opposite_face_label / single / answer_only / sample 6144008333654395

- `instance_seed`: `6144008333654395`
- `word_count`: `47`
- `body_word_count`: `47`

```text
The image shows a labeled cube net with one marked reference face and labeled face options. Choose the option for the face opposite the marked reference face.
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"D"}.
```

### task_puzzles__cyclic_order__cyclic_order_equivalent_label / single / answer_and_annotation / sample 1872563205023946

- `instance_seed`: `1872563205023946`
- `word_count`: `78`
- `body_word_count`: `69`

```text
The figure shows a reference token loop above six labeled option loops. Use the outlined token shapes when comparing cyclic order. Identify the single valid option loop. A valid loop may be rotated but not reflected.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] around the selected option loop image.
Return both fields in JSON.
Example JSON:
{"annotation":[574,463,746,617],"answer":"C"}
```

### task_puzzles__cyclic_order__cyclic_order_equivalent_label / single / answer_only / sample 1872563205023946

- `instance_seed`: `1872563205023946`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The figure shows a reference token loop above six labeled option loops. Use the outlined token shapes when comparing cyclic order. Identify the single valid option loop. A valid loop may be rotated but not reflected.
Set answer to the single option label as a capital letter.
Example JSON:
{"answer":"C"}
```

### task_puzzles__cyclic_order__insertion_position_label / single / answer_and_annotation / sample 6492238051144079

- `instance_seed`: `6492238051144079`
- `word_count`: `84`
- `body_word_count`: `75`

```text
The puzzle diagram shows a reference route loop and a partial loop with labeled gaps. Use the token colors when comparing cyclic order. One token from the reference is absent from the partial loop. Which labeled gap restores the reference cyclic order?
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] around the selected labeled gap badge.
Return both fields in JSON.
Example JSON:
{"annotation":[755,231,793,269],"answer":"C"}
```

### task_puzzles__cyclic_order__insertion_position_label / single / answer_only / sample 6492238051144079

- `instance_seed`: `6492238051144079`
- `word_count`: `63`
- `body_word_count`: `59`

```text
The puzzle diagram shows a reference route loop and a partial loop with labeled gaps. Use the token colors when comparing cyclic order. One token from the reference is absent from the partial loop. Which labeled gap restores the reference cyclic order?
Set answer to the single option label as a capital letter.
Return the option label in JSON.
Example JSON:
{"answer":"C"}
```

### task_puzzles__cyclic_order__swap_repair_label / single / answer_and_annotation / sample 4898275474869701

- `instance_seed`: `4898275474869701`
- `word_count`: `86`
- `body_word_count`: `77`

```text
The figure shows a reference charm loop, a broken numbered loop, and six swap options. Use the token colors when comparing cyclic order. Select the only swap option that repairs the broken loop into a rotated copy of the reference order.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] around the selected swap option card.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[493,425,707,521],"answer":"C"}
```

### task_puzzles__cyclic_order__swap_repair_label / single / answer_only / sample 4898275474869701

- `instance_seed`: `4898275474869701`
- `word_count`: `64`
- `body_word_count`: `60`

```text
The figure shows a reference charm loop, a broken numbered loop, and six swap options. Use the token colors when comparing cyclic order. Select the only swap option that repairs the broken loop into a rotated copy of the reference order.
Set answer to the single option label as a capital letter.
Use this JSON shape for the final response.
Example JSON:
{"answer":"C"}
```

### task_puzzles__matchstick__equation_repair_stick_label / single / answer_and_annotation / sample 8090816052123110

- `instance_seed`: `8090816052123110`
- `word_count`: `68`
- `body_word_count`: `68`

```text
The figure shows a false matchstick equation with labeled digit sticks. Remove exactly one labeled stick. Which label makes the equation true?
Set answer to the single option label as a capital letter.
Set annotation to the selected stick segment in image pixels as [[x1, y1], [x2, y2]], using the centerline endpoints of that stick.
Write only a JSON object like {"annotation":[[240,180],[312,180]],"answer":"B"}.
```

### task_puzzles__matchstick__equation_repair_stick_label / single / answer_only / sample 8090816052123110

- `instance_seed`: `8090816052123110`
- `word_count`: `42`
- `body_word_count`: `42`

```text
The figure shows a false matchstick equation with labeled digit sticks. Remove exactly one labeled stick. Which label makes the equation true?
Set answer to the single option label as a capital letter.
Use the answer-only JSON shape shown here: {"answer":"B"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / add_one_stick / answer_and_annotation / sample 8775820870254963

- `instance_seed`: `8775820870254963`
- `word_count`: `83`
- `body_word_count`: `83`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by adding exactly one stick to the Source.
Set answer to the single option label as a capital letter.
Set annotation to a bbox_map in image pixels with keys source_number and selected_option. Each key maps to one bounding box [x0, y0, x1, y1].
Use the answer-and-annotation JSON shape shown here: {"annotation":{"source_number":[58,58,1142,288],"selected_option":[440,332,760,550]},"answer":"B"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / add_one_stick / answer_only / sample 8775820870254963

- `instance_seed`: `8775820870254963`
- `word_count`: `46`
- `body_word_count`: `46`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by adding exactly one stick to the Source.
Set answer to the single option label as a capital letter.
Return the answer in JSON: {"answer":"B"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / remove_one_stick / answer_and_annotation / sample 2862873540596054

- `instance_seed`: `2862873540596054`
- `word_count`: `84`
- `body_word_count`: `84`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by removing exactly one stick from the Source.
Set answer to the single option label as a capital letter.
Set annotation to a bbox_map in image pixels with keys source_number and selected_option. Each key maps to one bounding box [x0, y0, x1, y1].
Use this JSON shape for the final response: {"annotation":{"source_number":[58,58,1142,288],"selected_option":[440,332,760,550]},"answer":"B"}.
```

### task_puzzles__matchstick__matchstick_number_transform_label / remove_one_stick / answer_only / sample 2862873540596054

- `instance_seed`: `2862873540596054`
- `word_count`: `49`
- `body_word_count`: `49`

```text
The image shows a Source matchstick number and six labeled candidate numbers. Select the candidate number that can be formed by removing exactly one stick from the Source.
Set answer to the single option label as a capital letter.
Use this JSON shape for the final response: {"answer":"B"}.
```

### task_puzzles__matchstick__max_square_count_after_additions_value / single / answer_and_annotation / sample 1369794825561587

- `instance_seed`: `1369794825561587`
- `word_count`: `85`
- `body_word_count`: `85`

```text
The puzzle diagram shows a matchstick square lattice with some empty grid edges. Place exactly 1 more matchsticks on empty grid edges. How many complete unit squares can there be at most?
Set answer to the maximum number of complete unit squares that can be present.
Set annotation to a bbox_set in image pixels, one bounding box [x0, y0, x1, y1] for each complete unit square counted in the final board.
Return JSON like {"annotation":[[126,118,226,218],[226,118,326,218]],"answer":2}.
```

### task_puzzles__matchstick__max_square_count_after_additions_value / single / answer_only / sample 1369794825561587

- `instance_seed`: `1369794825561587`
- `word_count`: `56`
- `body_word_count`: `56`

```text
The puzzle diagram shows a matchstick square lattice with some empty grid edges. Place exactly 1 more matchsticks on empty grid edges. How many complete unit squares can there be at most?
Set answer to the maximum number of complete unit squares that can be present.
Use this JSON shape for the final response: {"answer":2}.
```

### task_puzzles__maze__exit_reachability_label / single / answer_and_annotation / sample 6050110445753073

- `instance_seed`: `6050110445753073`
- `word_count`: `69`
- `body_word_count`: `62`

```text
The visual shows a heavy-wall orthogonal maze with a START cell and labeled exits on the outer boundary. Which labeled exit is reachable from START? There is exactly one such exit.
Set answer to the selected exit label as a string.
Set annotation to one image-pixel point [x,y] centered on the selected exit marker.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[194,118],"answer":"C"}
```

### task_puzzles__maze__exit_reachability_label / single / answer_only / sample 6050110445753073

- `instance_seed`: `6050110445753073`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The visual shows a heavy-wall orthogonal maze with a START cell and labeled exits on the outer boundary. Which labeled exit is reachable from START? There is exactly one such exit.
Set answer to the selected exit label as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"C"}
```

### task_puzzles__maze__nearest_exit_label / single / answer_and_annotation / sample 1259047097857958

- `instance_seed`: `1259047097857958`
- `word_count`: `73`
- `body_word_count`: `66`

```text
This maze shows a paper-style orthogonal wall maze with a START cell and labeled exits on the outer boundary. What is the label of the exit nearest to START through the maze corridors?
Set answer to the selected exit label as a string.
Set annotation to one image-pixel point [x,y] centered on the selected nearest exit marker.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[194,118],"answer":"C"}
```

### task_puzzles__maze__nearest_exit_label / single / answer_only / sample 1259047097857958

- `instance_seed`: `1259047097857958`
- `word_count`: `54`
- `body_word_count`: `50`

```text
This maze shows a paper-style orthogonal wall maze with a START cell and labeled exits on the outer boundary. What is the label of the exit nearest to START through the maze corridors?
Set answer to the selected exit label as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"C"}
```

### task_puzzles__nonogram__candidate_solution_label / single / answer_and_annotation / sample 2307166374885084

- `instance_seed`: `2307166374885084`
- `word_count`: `69`
- `body_word_count`: `60`

```text
The puzzle diagram shows a card-style nonogram clue grid with labeled filled-grid options. Select the filled-grid option that matches every row clue and every column clue.
Set answer to the selected candidate-grid option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected candidate grid option panel.
Return both fields in JSON.
Example JSON:
{"annotation":[622,650,768,776],"answer":"D"}
```

### task_puzzles__nonogram__candidate_solution_label / single / answer_only / sample 2307166374885084

- `instance_seed`: `2307166374885084`
- `word_count`: `49`
- `body_word_count`: `45`

```text
The puzzle diagram shows a card-style nonogram clue grid with labeled filled-grid options. Select the filled-grid option that matches every row clue and every column clue.
Set answer to the selected candidate-grid option letter as a string.
Use this JSON shape for the final response.
Example JSON:
{"answer":"D"}
```

### task_puzzles__nonogram__line_completion_label / single / answer_and_annotation / sample 4079095489109925

- `instance_seed`: `4079095489109925`
- `word_count`: `70`
- `body_word_count`: `61`

```text
This nonogram shows a blueprint-style nonogram clue grid with one marked row and labeled row-strip options. Select the row-strip option that satisfies the marked clue and matches the visible cells in row 5.
Set answer to the selected strip option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected strip option panel.
Example JSON:
{"annotation":[462,650,608,776],"answer":"C"}
```

### task_puzzles__nonogram__line_completion_label / single / answer_only / sample 4079095489109925

- `instance_seed`: `4079095489109925`
- `word_count`: `55`
- `body_word_count`: `51`

```text
This nonogram shows a blueprint-style nonogram clue grid with one marked row and labeled row-strip options. Select the row-strip option that satisfies the marked clue and matches the visible cells in row 5.
Set answer to the selected strip option letter as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"C"}
```

### task_puzzles__pipe_flow__misrotated_tile_label / single / answer_and_annotation / sample 7765548981679743

- `instance_seed`: `7765548981679743`
- `word_count`: `94`
- `body_word_count`: `85`

```text
The image shows a circuit-trace tile grid with a green start marker and a red triangular finish flag. One labeled pipe tile is rotated away from its correct orientation. Which label marks the tile that should be rotated to restore the path from the green start marker to the red finish flag?
Set answer to the selected tile letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the tile that should be rotated.
Return both fields in JSON.
Example JSON:
{"annotation":[376,248,420,286],"answer":"B"}
```

### task_puzzles__pipe_flow__misrotated_tile_label / single / answer_only / sample 7765548981679743

- `instance_seed`: `7765548981679743`
- `word_count`: `73`
- `body_word_count`: `69`

```text
The image shows a circuit-trace tile grid with a green start marker and a red triangular finish flag. One labeled pipe tile is rotated away from its correct orientation. Which label marks the tile that should be rotated to restore the path from the green start marker to the red finish flag?
Set answer to the selected tile letter as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"B"}
```

### task_puzzles__pipe_flow__pipe_flow_repair_tile_label / single / answer_and_annotation / sample 277694648037652

- `instance_seed`: `277694648037652`
- `word_count`: `100`
- `body_word_count`: `85`

```text
The figure shows a pipe-tile grid with a green start marker and a red triangular finish flag. Which labeled 2x2 repair piece fits the missing black region as shown and restores flow from the green start marker to the red finish flag?
Set answer to the selected repair option letter as a string.
Set annotation to an object with keys "selected_option" and "missing_gap". Each value is one image-pixel bounding box [x0,y0,x1,y1] around that visual witness.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":{"selected_option":[774,248,902,376],"missing_gap":[424,312,512,400]},"answer":"C"}
```

### task_puzzles__pipe_flow__pipe_flow_repair_tile_label / single / answer_only / sample 277694648037652

- `instance_seed`: `277694648037652`
- `word_count`: `57`
- `body_word_count`: `53`

```text
The figure shows a pipe-tile grid with a green start marker and a red triangular finish flag. Which labeled 2x2 repair piece fits the missing black region as shown and restores flow from the green start marker to the red finish flag?
Set answer to the selected repair option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_puzzles__polyomino_assembly__composition_result_label / single / answer_and_annotation / sample 7224039817153389

- `instance_seed`: `7224039817153389`
- `word_count`: `64`
- `body_word_count`: `55`

```text
The visual shows two source polyomino pieces and four labeled candidate result shapes. Choose the option that the two source pieces can form exactly using moves and rotations only.
Set answer to the capital letter of the chosen option.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option card.
Example JSON:
{"annotation":[438,332,762,522],"answer":"B"}
```

### task_puzzles__polyomino_assembly__composition_result_label / single / answer_only / sample 7224039817153389

- `instance_seed`: `7224039817153389`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The visual shows two source polyomino pieces and four labeled candidate result shapes. Choose the option that the two source pieces can form exactly using moves and rotations only.
Set answer to the option label.
Example JSON:
{"answer":"B"}
```

### task_puzzles__polyomino_assembly__decomposition_pair_label / single / answer_and_annotation / sample 1404431216412292

- `instance_seed`: `1404431216412292`
- `word_count`: `69`
- `body_word_count`: `60`

```text
This puzzle diagram shows a target polyomino and four labeled options, each containing two candidate pieces. Choose the option whose two pieces can form the target polyomino exactly using moves and rotations only.
Set answer to the single option label as a capital letter.
Set annotation to the image-pixel bounding box [x0,y0,x1,y1] of the chosen option card.
Example JSON:
{"annotation":[438,332,762,522],"answer":"B"}
```

### task_puzzles__polyomino_assembly__decomposition_pair_label / single / answer_only / sample 1404431216412292

- `instance_seed`: `1404431216412292`
- `word_count`: `53`
- `body_word_count`: `49`

```text
This puzzle diagram shows a target polyomino and four labeled options, each containing two candidate pieces. Choose the option whose two pieces can form the target polyomino exactly using moves and rotations only.
Set answer to the single option label as a capital letter.
Use this answer-only JSON shape.
Example JSON:
{"answer":"B"}
```

### task_puzzles__raven_matrix__raven_analogical_transform_label / single / answer_and_annotation / sample 243953950788786

- `instance_seed`: `243953950788786`
- `word_count`: `72`
- `body_word_count`: `63`

```text
The puzzle diagram shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Identify the option that completes the 3 by 3 matrix under the attribute rule.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Return both fields in JSON.
Example JSON:
{"annotation":[793,647,899,752],"answer":"D"}
```

### task_puzzles__raven_matrix__raven_analogical_transform_label / single / answer_only / sample 243953950788786

- `instance_seed`: `243953950788786`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The puzzle diagram shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Identify the option that completes the 3 by 3 matrix under the attribute rule.
Set answer to the selected option letter as a string.
Write only a JSON object in this shape.
Example JSON:
{"answer":"D"}
```

### task_puzzles__raven_matrix__raven_count_progression_label / single / answer_and_annotation / sample 8850507673529605

- `instance_seed`: `8850507673529605`
- `word_count`: `77`
- `body_word_count`: `68`

```text
The visual shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Which labeled option completes the matrix when the visible rule is about counts of filled mini-grid cells?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[465,647,571,752],"answer":"B"}
```

### task_puzzles__raven_matrix__raven_count_progression_label / single / answer_only / sample 8850507673529605

- `instance_seed`: `8850507673529605`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The visual shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Which labeled option completes the matrix when the visible rule is about counts of filled mini-grid cells?
Set answer to the selected option letter as a string.
Example JSON:
{"answer":"B"}
```

### task_puzzles__raven_matrix__raven_feature_binding_label / single / answer_and_annotation / sample 7303803524000724

- `instance_seed`: `7303803524000724`
- `word_count`: `80`
- `body_word_count`: `71`

```text
The image shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Use how two visual properties vary systematically across the matrix to choose the option that completes the missing lower-right cell.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[629,647,735,752],"answer":"C"}
```

### task_puzzles__raven_matrix__raven_feature_binding_label / single / answer_only / sample 7303803524000724

- `instance_seed`: `7303803524000724`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The image shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Use how two visual properties vary systematically across the matrix to choose the option that completes the missing lower-right cell.
Set answer to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_puzzles__raven_matrix__raven_position_progression_label / single / answer_and_annotation / sample 3049575876342859

- `instance_seed`: `3049575876342859`
- `word_count`: `67`
- `body_word_count`: `58`

```text
The scene shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Select the option whose marker position fits the matrix progression.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Return both fields in JSON.
Example JSON:
{"annotation":[301,647,407,752],"answer":"A"}
```

### task_puzzles__raven_matrix__raven_position_progression_label / single / answer_only / sample 3049575876342859

- `instance_seed`: `3049575876342859`
- `word_count`: `49`
- `body_word_count`: `45`

```text
The scene shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Select the option whose marker position fits the matrix progression.
Set answer to the selected option letter as a string.
Write only a JSON object in this shape.
Example JSON:
{"answer":"A"}
```

### task_puzzles__raven_matrix__raven_set_operation_label / single / answer_and_annotation / sample 6592776187159996

- `instance_seed`: `6592776187159996`
- `word_count`: `72`
- `body_word_count`: `63`

```text
This figure shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Identify the option that completes the 3 by 3 matrix under the filled-cell combination rule.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Return both fields in JSON.
Example JSON:
{"annotation":[629,647,735,752],"answer":"C"}
```

### task_puzzles__raven_matrix__raven_set_operation_label / single / answer_only / sample 6592776187159996

- `instance_seed`: `6592776187159996`
- `word_count`: `53`
- `body_word_count`: `49`

```text
This figure shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Identify the option that completes the 3 by 3 matrix under the filled-cell combination rule.
Set answer to the selected option letter as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"C"}
```

### task_puzzles__raven_matrix__raven_spatial_transform_label / single / answer_and_annotation / sample 1262953292127848

- `instance_seed`: `1262953292127848`
- `word_count`: `73`
- `body_word_count`: `64`

```text
This figure shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Which labeled option completes the matrix when the visible rule changes the filled-cell arrangement?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the correct option cell.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[793,647,899,752],"answer":"D"}
```

### task_puzzles__raven_matrix__raven_spatial_transform_label / single / answer_only / sample 1262953292127848

- `instance_seed`: `1262953292127848`
- `word_count`: `52`
- `body_word_count`: `48`

```text
This figure shows a 3 by 3 Raven-style matrix puzzle with four labeled image options below it. Which labeled option completes the matrix when the visible rule changes the filled-cell arrangement?
Set answer to the selected option letter as a string.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"D"}
```

### task_puzzles__rubiks_net__post_move_face_color_count_label / single / answer_and_annotation / sample 240126542032281

- `instance_seed`: `240126542032281`
- `word_count`: `90`
- `body_word_count`: `81`

```text
The scene shows a Rubik-style cube net with face labels, a Target color swatch, and four labeled number options; a prime mark means counterclockwise as viewed from outside the turned face. Use moves U'; which number option counts stickers matching the Target color on the Left face?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected option panel.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[836,492,972,646],"answer":"A"}
```

### task_puzzles__rubiks_net__post_move_face_color_count_label / single / answer_only / sample 240126542032281

- `instance_seed`: `240126542032281`
- `word_count`: `66`
- `body_word_count`: `62`

```text
The scene shows a Rubik-style cube net with face labels, a Target color swatch, and four labeled number options; a prime mark means counterclockwise as viewed from outside the turned face. Use moves U'; which number option counts stickers matching the Target color on the Left face?
Set answer to the selected option letter as a string.
Return the answer in JSON.
Example JSON:
{"answer":"A"}
```

### task_puzzles__rubiks_net__post_move_sticker_color_label / single / answer_and_annotation / sample 6658997801619891

- `instance_seed`: `6658997801619891`
- `word_count`: `90`
- `body_word_count`: `81`

```text
The visual shows a Rubik-style cube net with face labels, a (column,row) coordinate reference, and four labeled color-swatch options; a prime mark means counterclockwise as viewed from outside the turned face. Choose the swatch for position (2, 2) on the Right face after applying U F.
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected option panel.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[990,126,1126,280],"answer":"C"}
```

### task_puzzles__rubiks_net__post_move_sticker_color_label / single / answer_only / sample 6658997801619891

- `instance_seed`: `6658997801619891`
- `word_count`: `66`
- `body_word_count`: `62`

```text
The visual shows a Rubik-style cube net with face labels, a (column,row) coordinate reference, and four labeled color-swatch options; a prime mark means counterclockwise as viewed from outside the turned face. Choose the swatch for position (2, 2) on the Right face after applying U F.
Set answer to the selected option letter as a string.
Return the answer in JSON.
Example JSON:
{"answer":"C"}
```

### task_puzzles__rubiks_net__rubiks_move_result_label / direct_sequence_result_label / answer_and_annotation / sample 3808764587814892

- `instance_seed`: `3808764587814892`
- `word_count`: `75`
- `body_word_count`: `66`

```text
The visual shows a Rubik-style starting cube net with face labels and four labeled candidate result nets; a prime mark means counterclockwise as viewed from outside the turned face. Which candidate net shows the state after applying D L'?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected candidate-net option panel.
Example JSON:
{"annotation":[292,536,490,724],"answer":"B"}
```

### task_puzzles__rubiks_net__rubiks_move_result_label / direct_sequence_result_label / answer_only / sample 3808764587814892

- `instance_seed`: `3808764587814892`
- `word_count`: `58`
- `body_word_count`: `54`

```text
The visual shows a Rubik-style starting cube net with face labels and four labeled candidate result nets; a prime mark means counterclockwise as viewed from outside the turned face. Which candidate net shows the state after applying D L'?
Set answer to the selected option letter as a string.
Return the answer in JSON.
Example JSON:
{"answer":"B"}
```

### task_puzzles__rubiks_net__rubiks_move_result_label / inverse_sequence_result_label / answer_and_annotation / sample 8716402677758859

- `instance_seed`: `8716402677758859`
- `word_count`: `78`
- `body_word_count`: `69`

```text
The puzzle diagram shows a Rubik-style starting cube net with face labels and four labeled candidate result nets; a prime mark means counterclockwise as viewed from outside the turned face. Which option shows the state after applying the inverse of R D?
Set answer to the selected option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected candidate-net option panel.
Example JSON:
{"annotation":[292,536,490,724],"answer":"B"}
```

### task_puzzles__rubiks_net__rubiks_move_result_label / inverse_sequence_result_label / answer_only / sample 8716402677758859

- `instance_seed`: `8716402677758859`
- `word_count`: `56`
- `body_word_count`: `52`

```text
The puzzle diagram shows a Rubik-style starting cube net with face labels and four labeled candidate result nets; a prime mark means counterclockwise as viewed from outside the turned face. Which option shows the state after applying the inverse of R D?
Set answer to the selected option letter as a string.
Example JSON:
{"answer":"B"}
```

### task_puzzles__sheet_transform__fold_cut_result_label / single / answer_and_annotation / sample 614779892116511

- `instance_seed`: `614779892116511`
- `word_count`: `74`
- `body_word_count`: `65`

```text
The image shows a paper fold-and-cut puzzle with a fold diagram above labeled unfolded-result options. Which option shows the unfolded paper after the indicated fold or folds and cut?
Set answer to the selected unfolded-result option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected unfolded-result option panel.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[134,420,312,598],"answer":"A"}
```

### task_puzzles__sheet_transform__fold_cut_result_label / single / answer_only / sample 614779892116511

- `instance_seed`: `614779892116511`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The image shows a paper fold-and-cut puzzle with a fold diagram above labeled unfolded-result options. Which option shows the unfolded paper after the indicated fold or folds and cut?
Set answer to the selected unfolded-result option letter as a string.
Use this JSON shape for the final response.
Example JSON:
{"answer":"A"}
```

### task_puzzles__sheet_transform__fold_projection_result_label / single / answer_and_annotation / sample 6680727329238135

- `instance_seed`: `6680727329238135`
- `word_count`: `70`
- `body_word_count`: `61`

```text
The visual shows a paper-folding puzzle with a fold diagram above labeled result options. Which option shows the mark pattern after applying the indicated fold?
Set answer to the selected folded-result option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected folded-result option panel.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[206,388,324,613],"answer":"A"}
```

### task_puzzles__sheet_transform__fold_projection_result_label / single / answer_only / sample 6680727329238135

- `instance_seed`: `6680727329238135`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The visual shows a paper-folding puzzle with a fold diagram above labeled result options. Which option shows the mark pattern after applying the indicated fold?
Set answer to the selected folded-result option letter as a string.
Write only a JSON object in this shape.
Example JSON:
{"answer":"A"}
```

### task_puzzles__sheet_transform__overlay_union_result_label / single / answer_and_annotation / sample 7430274865515133

- `instance_seed`: `7430274865515133`
- `word_count`: `77`
- `body_word_count`: `68`

```text
The puzzle diagram shows a card-style transparent-sheet overlay puzzle with two aligned source sheets above labeled result options. Mentally stack the two transparent sheets. Which labeled option shows the resulting set of marks?
Set answer to the selected overlay-result option letter as a string.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected result option panel.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[521,384,679,542],"answer":"B"}
```

### task_puzzles__sheet_transform__overlay_union_result_label / single / answer_only / sample 7430274865515133

- `instance_seed`: `7430274865515133`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The puzzle diagram shows a card-style transparent-sheet overlay puzzle with two aligned source sheets above labeled result options. Mentally stack the two transparent sheets. Which labeled option shows the resulting set of marks?
Set answer to the selected overlay-result option letter as a string.
Example JSON:
{"answer":"B"}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_column_count / answer_and_annotation / sample 2869593182357784

- `instance_seed`: `2869593182357784`
- `word_count`: `103`
- `body_word_count`: `90`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Use the visible stars and the Star Battle rules: one star in each row, column, and colored region, and no two stars touching. How many possible star placements remain in the marked column?
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked column; answer should be the count of legal star cells in the marked column.
Example JSON:
{"annotation":[[402,276,466,340],[402,468,466,532]],"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_column_count / answer_only / sample 2869593182357784

- `instance_seed`: `2869593182357784`
- `word_count`: `73`
- `body_word_count`: `69`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Use the visible stars and the Star Battle rules: one star in each row, column, and colored region, and no two stars touching. How many possible star placements remain in the marked column?
Write the answer field as the count of legal star cells in the marked column.
Example JSON:
{"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_region_count / answer_and_annotation / sample 4468537011817492

- `instance_seed`: `4468537011817492`
- `word_count`: `103`
- `body_word_count`: `90`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Apply the Star Battle rules: one star per row, column, and colored region; stars cannot touch by edge or corner. Within the marked region, count every cell where another star could be placed.
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked region; answer should be the count of legal star cells in the marked region.
Example JSON:
{"annotation":[[402,276,466,340],[466,340,530,404]],"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_region_count / answer_only / sample 4468537011817492

- `instance_seed`: `4468537011817492`
- `word_count`: `71`
- `body_word_count`: `67`

```text
The image shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. Apply the Star Battle rules: one star per row, column, and colored region; stars cannot touch by edge or corner. Within the marked region, count every cell where another star could be placed.
Set answer to the count of legal star cells in the marked region.
Example JSON:
{"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_row_count / answer_and_annotation / sample 6297137922527172

- `instance_seed`: `6297137922527172`
- `word_count`: `102`
- `body_word_count`: `89`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. In Star Battle, every row, column, and colored region needs exactly one star, and no two stars may touch, even diagonally. Count the legal remaining star cells inside the marked row.
Annotation should be a JSON array of image-pixel bboxes [x0,y0,x1,y1], one for each counted legal cell in the marked row; answer should be the count of legal star cells in the marked row.
Example JSON:
{"annotation":[[402,276,466,340],[530,276,594,340]],"answer":2}
```

### task_puzzles__star_battle__remaining_valid_cell_count / remaining_valid_cells_in_marked_row_count / answer_only / sample 6297137922527172

- `instance_seed`: `6297137922527172`
- `word_count`: `72`
- `body_word_count`: `68`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and one marked row, column, or region. In Star Battle, every row, column, and colored region needs exactly one star, and no two stars may touch, even diagonally. Count the legal remaining star cells inside the marked row.
Write the answer field as the count of legal star cells in the marked row.
Example JSON:
{"answer":2}
```

### task_puzzles__star_battle__valid_cell_anywhere_label / single / answer_and_annotation / sample 892184768993533

- `instance_seed`: `892184768993533`
- `word_count`: `80`
- `body_word_count`: `71`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and labeled candidate cells. Use these Star Battle rules: each row, column, and colored region must contain exactly one star; stars cannot touch, even diagonally. Which candidate label marks a legal remaining star cell?
Return annotation as [x0,y0,x1,y1], the image-pixel bbox of the selected candidate cell and answer as the legal candidate letter.
Example JSON:
{"annotation":[402,276,466,340],"answer":"C"}
```

### task_puzzles__star_battle__valid_cell_anywhere_label / single / answer_only / sample 892184768993533

- `instance_seed`: `892184768993533`
- `word_count`: `61`
- `body_word_count`: `57`

```text
This puzzle diagram shows a partially filled Star Battle grid with colored regions, visible stars, and labeled candidate cells. Use these Star Battle rules: each row, column, and colored region must contain exactly one star; stars cannot touch, even diagonally. Which candidate label marks a legal remaining star cell?
Use the legal candidate letter for the answer.
Example JSON:
{"answer":"C"}
```

### task_puzzles__sudoku__marked_cell_candidate_count / single / answer_and_annotation / sample 1636457636102279

- `instance_seed`: `1636457636102279`
- `word_count`: `67`
- `body_word_count`: `58`

```text
The visual shows a partially filled Sudoku grid. Count the legal candidate digits for the marked empty Sudoku cell.
Set answer to the number of legal candidate digits for the marked empty cell.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the red outlined marked cell.
Write only a JSON object in this shape.
Example JSON:
{"annotation":[140,220,210,290],"answer":3}
```

### task_puzzles__sudoku__marked_cell_candidate_count / single / answer_only / sample 1636457636102279

- `instance_seed`: `1636457636102279`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The visual shows a partially filled Sudoku grid. Count the legal candidate digits for the marked empty Sudoku cell.
Set answer to the number of legal candidate digits for the marked empty cell.
Use this JSON shape for the final response.
Example JSON:
{"answer":3}
```

### task_puzzles__sudoku__marked_cell_value / single / answer_and_annotation / sample 2757075097203723

- `instance_seed`: `2757075097203723`
- `word_count`: `78`
- `body_word_count`: `69`

```text
This scene shows a partially filled Sudoku grid. Rows, columns, and 3 by 3 boxes cannot repeat digits 1 through 9. Which digit must be placed in the marked empty cell?
Set answer to the digit that must go in the marked empty cell.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the red outlined marked cell.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[140,220,210,290],"answer":7}
```

### task_puzzles__sudoku__marked_cell_value / single / answer_only / sample 2757075097203723

- `instance_seed`: `2757075097203723`
- `word_count`: `56`
- `body_word_count`: `52`

```text
This scene shows a partially filled Sudoku grid. Rows, columns, and 3 by 3 boxes cannot repeat digits 1 through 9. Which digit must be placed in the marked empty cell?
Set answer to the digit that must go in the marked empty cell.
Use this JSON shape for the final response.
Example JSON:
{"answer":7}
```

### task_puzzles__sudoku__mistake_cell_label / single / answer_and_annotation / sample 7617357225234053

- `instance_seed`: `7617357225234053`
- `word_count`: `60`
- `body_word_count`: `51`

```text
The scene shows a more filled Sudoku grid. Using standard Sudoku rules, choose the lettered filled cell whose digit is wrong.
Set answer to the option letter of the filled cell with the wrong digit.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the selected lettered cell.
Example JSON:
{"annotation":[140,220,210,290],"answer":"B"}
```

### task_puzzles__sudoku__mistake_cell_label / single / answer_only / sample 7617357225234053

- `instance_seed`: `7617357225234053`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The scene shows a more filled Sudoku grid. Using standard Sudoku rules, choose the lettered filled cell whose digit is wrong.
Set answer to the option letter of the filled cell with the wrong digit.
Example JSON:
{"answer":"B"}
```

### task_puzzles__tents__missing_tent_cell_label / single / answer_and_annotation / sample 7739839479435094

- `instance_seed`: `7739839479435094`
- `word_count`: `92`
- `body_word_count`: `83`

```text
The image shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. Find the only labeled candidate cell where the marked tree's missing tent can be placed while satisfying the clues and no-touch rule.
Set answer to the label of the only candidate cell where the marked tree's missing tent can be placed.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the selected candidate cell.
Return both fields in JSON.
Example JSON:
{"annotation":[512,386,574,448],"answer":"C"}
```

### task_puzzles__tents__missing_tent_cell_label / single / answer_only / sample 7739839479435094

- `instance_seed`: `7739839479435094`
- `word_count`: `71`
- `body_word_count`: `67`

```text
The image shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. Find the only labeled candidate cell where the marked tree's missing tent can be placed while satisfying the clues and no-touch rule.
Set answer to the label of the only candidate cell where the marked tree's missing tent can be placed.
Return the answer in JSON.
Example JSON:
{"answer":"C"}
```

### task_puzzles__tents__violating_tent_label / single / answer_and_annotation / sample 1869727188121144

- `instance_seed`: `1869727188121144`
- `word_count`: `92`
- `body_word_count`: `83`

```text
The figure shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. A tent must be directly above, below, left, or right of a tree. Which labeled tent is not next to any tree?
Set answer to the label of the tent that is not orthogonally adjacent to any tree.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] for the selected labeled tent cell.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[356,226,416,286],"answer":"B"}
```

### task_puzzles__tents__violating_tent_label / single / answer_only / sample 1869727188121144

- `instance_seed`: `1869727188121144`
- `word_count`: `71`
- `body_word_count`: `67`

```text
The figure shows a blueprint-style Tents puzzle grid with row and column clues, trees, visible tents, and labeled cells or tents. A tent must be directly above, below, left, or right of a tree. Which labeled tent is not next to any tree?
Set answer to the label of the tent that is not orthogonally adjacent to any tree.
Use this JSON shape for the final response.
Example JSON:
{"answer":"B"}
```

### task_puzzles__toggle_grid__toggle_repair_switch_label / single / answer_and_annotation / sample 7583662374170743

- `instance_seed`: `7583662374170743`
- `word_count`: `80`
- `body_word_count`: `71`

```text
The scene shows a toggle grid with switch cells, binary cell states, and visual answer options. One labeled switch press transforms the start grid into the target grid using the orthogonal-neighbor toggle rule. Which label is it?
Set answer to the label of the switch cell that transforms the start grid into the target grid.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected switch cell.
Example JSON:
{"annotation":[210,286,282,358],"answer":"C"}
```

### task_puzzles__toggle_grid__toggle_repair_switch_label / single / answer_only / sample 7583662374170743

- `instance_seed`: `7583662374170743`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The scene shows a toggle grid with switch cells, binary cell states, and visual answer options. One labeled switch press transforms the start grid into the target grid using the orthogonal-neighbor toggle rule. Which label is it?
Set answer to the label of the switch cell that transforms the start grid into the target grid.
Example JSON:
{"answer":"C"}
```

### task_puzzles__toggle_grid__toggle_result_label / single / answer_and_annotation / sample 8623333450752672

- `instance_seed`: `8623333450752672`
- `word_count`: `87`
- `body_word_count`: `78`

```text
The figure shows a notebook-style toggle grid with switch cells, binary cell states, and visual answer options. Apply the visible red switch press to the start grid using the orthogonal-neighbor toggle rule. Which labeled result grid is produced?
Set answer to the label of the result-grid option produced by pressing the red marked switch.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected result option panel.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[722,552,882,806],"answer":"D"}
```

### task_puzzles__toggle_grid__toggle_result_label / single / answer_only / sample 8623333450752672

- `instance_seed`: `8623333450752672`
- `word_count`: `66`
- `body_word_count`: `62`

```text
The figure shows a notebook-style toggle grid with switch cells, binary cell states, and visual answer options. Apply the visible red switch press to the start grid using the orthogonal-neighbor toggle rule. Which labeled result grid is produced?
Set answer to the label of the result-grid option produced by pressing the red marked switch.
Use this JSON shape for the final response.
Example JSON:
{"answer":"D"}
```

### task_puzzles__voxel_cube__cube_count / single / answer_and_annotation / sample 6499340710497655

- `instance_seed`: `6499340710497655`
- `word_count`: `57`
- `body_word_count`: `48`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. How many unit cubes are in the shown voxel structure?
Set answer to the total unit-cube count as an integer.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the voxel structure.
Example JSON:
{"annotation":[310,170,590,520],"answer":9}
```

### task_puzzles__voxel_cube__cube_count / single / answer_only / sample 6499340710497655

- `instance_seed`: `6499340710497655`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. How many unit cubes are in the shown voxel structure?
Set answer to the total unit-cube count as an integer.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":9}
```

### task_puzzles__voxel_cube__cube_painted_face_count / single / answer_and_annotation / sample 602496028986470

- `instance_seed`: `602496028986470`
- `word_count`: `72`
- `body_word_count`: `63`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. Count the unit cubes with exactly 3 exposed painted faces.
Set answer to the count of cubes with exactly the requested number of painted faces as an integer.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the voxel structure.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[310,170,590,520],"answer":3}
```

### task_puzzles__voxel_cube__cube_painted_face_count / single / answer_only / sample 602496028986470

- `instance_seed`: `602496028986470`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. Count the unit cubes with exactly 3 exposed painted faces.
Set answer to the count of cubes with exactly the requested number of painted faces as an integer.
Return the answer in JSON.
Example JSON:
{"answer":3}
```

### task_puzzles__voxel_cube__cube_projection_match_label / single / answer_and_annotation / sample 2618662579511971

- `instance_seed`: `2618662579511971`
- `word_count`: `65`
- `body_word_count`: `56`

```text
The scene shows an isometric voxel-cube structure with orthographic projection panels when needed. Select the labeled option matching the structure's front projection.
Set answer to the label of the matching projection option.
Set annotation to one image-pixel bounding box [x0,y0,x1,y1] around the selected projection option panel.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[690,420,860,580],"answer":"C"}
```

### task_puzzles__voxel_cube__cube_projection_match_label / single / answer_only / sample 2618662579511971

- `instance_seed`: `2618662579511971`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The scene shows an isometric voxel-cube structure with orthographic projection panels when needed. Select the labeled option matching the structure's front projection.
Set answer to the label of the matching projection option.
Use the answer-only JSON shape shown here.
Example JSON:
{"answer":"C"}
```

### task_puzzles__voxel_cube__cube_structure_change_count / single / answer_and_annotation / sample 7764713121168464

- `instance_seed`: `7764713121168464`
- `word_count`: `81`
- `body_word_count`: `68`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. The reference shows the complete cuboid. How many cubes are absent from the changed version?
Set answer to the number of cubes that must be added as an integer.
Set annotation to a JSON array of image-pixel bounding boxes [x0,y0,x1,y1], one around each compared structure.
Use the answer-and-annotation JSON shape shown here.
Example JSON:
{"annotation":[[120,210,420,560],[520,225,820,560]],"answer":2}
```

### task_puzzles__voxel_cube__cube_structure_change_count / single / answer_only / sample 7764713121168464

- `instance_seed`: `7764713121168464`
- `word_count`: `46`
- `body_word_count`: `42`

```text
The figure shows an isometric voxel-cube structure with orthographic projection panels when needed. The reference shows the complete cuboid. How many cubes are absent from the changed version?
Set answer to the number of cubes that must be added as an integer.
Example JSON:
{"answer":2}
```

### task_puzzles__voxel_cube__cube_visible_projection_count / single / answer_and_annotation / sample 5668460865676647

- `instance_seed`: `5668460865676647`
- `word_count`: `75`
- `body_word_count`: `58`

```text
The image shows an isometric voxel-cube structure with orthographic projection panels when needed. In the front orthographic view, how many projection-grid cells should be filled?
Set answer to the filled projection-cell count as an integer.
Set annotation to a JSON array of image-pixel bounding boxes [x0,y0,x1,y1], one for each projection-grid cell that should be filled.
Example JSON:
{"annotation":[[620,250,662,292],[662,250,704,292],[620,292,662,334]],"answer":3}
```

### task_puzzles__voxel_cube__cube_visible_projection_count / single / answer_only / sample 5668460865676647

- `instance_seed`: `5668460865676647`
- `word_count`: `47`
- `body_word_count`: `43`

```text
The image shows an isometric voxel-cube structure with orthographic projection panels when needed. In the front orthographic view, how many projection-grid cells should be filled?
Set answer to the filled projection-cell count as an integer.
Use this JSON shape for the final response.
Example JSON:
{"answer":3}
```

### task_puzzles__word_search__present_word_option_label / single / answer_and_annotation / sample 2190261597316433

- `instance_seed`: `2190261597316433`
- `word_count`: `68`
- `body_word_count`: `59`

```text
The figure shows a row-and-column labeled word-search grid. Which labeled option below the grid names the word that is actually placed in the puzzle?
Set answer to the selected option letter.
Set annotation to one image-pixel line segment [[x1,y1],[x2,y2]] from the present word's first-letter cell center to its last-letter cell center.
Return both fields in JSON.
Example JSON:
{"annotation":[[223,251],[339,251]],"answer":"C"}
```

### task_puzzles__word_search__present_word_option_label / single / answer_only / sample 2190261597316433

- `instance_seed`: `2190261597316433`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The figure shows a row-and-column labeled word-search grid. Which labeled option below the grid names the word that is actually placed in the puzzle?
Set answer to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_puzzles__word_search__search_location_label / single / answer_and_annotation / sample 655130434197869

- `instance_seed`: `655130434197869`
- `word_count`: `89`
- `body_word_count`: `72`

```text
The word-search puzzle shows a row-and-column labeled word-search grid. Use the grid labels to locate "ABLE". Which option lists the correct start row, start column, and direction?
Set answer to the selected option letter.
Set annotation to a JSON array of ordered image-pixel bounding boxes [x0,y0,x1,y1], one for each grid cell in the found word from first letter to last letter.
Use this JSON shape for the final response.
Example JSON:
{"annotation":[[194,222,252,280],[252,222,310,280],[310,222,368,280]],"answer":"C"}
```

### task_puzzles__word_search__search_location_label / single / answer_only / sample 655130434197869

- `instance_seed`: `655130434197869`
- `word_count`: `46`
- `body_word_count`: `42`

```text
The word-search puzzle shows a row-and-column labeled word-search grid. Use the grid labels to locate "ABLE". Which option lists the correct start row, start column, and direction?
Set answer to the selected option letter.
Use this JSON shape for the final response.
Example JSON:
{"answer":"C"}
```
