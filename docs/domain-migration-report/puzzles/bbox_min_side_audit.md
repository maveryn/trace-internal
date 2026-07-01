# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-07-01T07:42:09Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `20`
- Tasks: `60`
- Bbox-family runtime tasks: `54`
- Samples inspected: `6000`
- Bboxes inspected: `7664`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| puzzles | arithmetic_panel | `task_puzzles__arithmetic_panel__equal_sum_line_constraint_value` | ['bbox'] | 100 | 100 | 34 | 34 | 34 | pass |
| puzzles | arithmetic_panel | `task_puzzles__arithmetic_panel__number_wall_value` | ['bbox'] | 100 | 100 | 45.6 | 32 | 32 | pass |
| puzzles | arithmetic_panel | `task_puzzles__arithmetic_panel__operation_table_cell_value` | ['bbox'] | 100 | 100 | 38 | 32 | 32 | pass |
| puzzles | arithmetic_panel | `task_puzzles__arithmetic_panel__row_column_total_missing_value` | ['bbox'] | 100 | 100 | 39 | 33 | 33 | pass |
| puzzles | arithmetic_panel | `task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value` | ['bbox'] | 100 | 100 | 32 | 32 | 32 | pass |
| puzzles | balance_scale | `task_puzzles__balance_scale__equivalent_object_count_value` | ['bbox'] | 100 | 100 | 44.308 | 40.28 | 40.28 | pass |
| puzzles | balance_scale | `task_puzzles__balance_scale__missing_object_weight_value` | ['bbox'] | 100 | 100 | 54.704 | 44.84 | 44.84 | pass |
| puzzles | balance_scale | `task_puzzles__balance_scale__query_side_relation_label` | ['bbox'] | 100 | 100 | 205.6 | 26 | 26 | pass |
| puzzles | balance_scale | `task_puzzles__balance_scale__weight_order_label` | ['bbox'] | 100 | 100 | 197 | 62 | 62 | pass |
| puzzles | cell_board | `task_puzzles__cell_board__largest_component_size` | ['bbox_set'] | 100 | 441 | 28 | 28 | 28 | pass |
| puzzles | cell_board | `task_puzzles__cell_board__reachable_region_size` | ['bbox_set'] | 100 | 461 | 28 | 28 | 28 | pass |
| puzzles | color_gradient | `task_puzzles__color_gradient__color_gradient_completion_label` | ['bbox'] | 100 | 100 | 57 | 57 | 57 | pass |
| puzzles | color_gradient | `task_puzzles__color_gradient__color_gradient_violation_cell_label` | ['bbox'] | 100 | 100 | 56 | 56 | 56 | pass |
| puzzles | cube_net | `task_puzzles__cube_net__equivalent_net_label` | ['bbox'] | 100 | 100 | 292 | 322 | 292 | pass |
| puzzles | cube_net | `task_puzzles__cube_net__marked_edge_neighbor_face_label` | ['bbox'] | 100 | 100 | 134 | 269 | 134 | pass |
| puzzles | cube_net | `task_puzzles__cube_net__opposite_face_label` | ['bbox'] | 100 | 100 | 134 | 269 | 134 | pass |
| puzzles | cyclic_order | `task_puzzles__cyclic_order__cyclic_order_equivalent_label` | ['bbox'] | 100 | 100 | 230 | 180 | 180 | pass |
| puzzles | cyclic_order | `task_puzzles__cyclic_order__insertion_position_label` | ['bbox'] | 100 | 100 | 39.6 | 39.6 | 39.6 | pass |
| puzzles | cyclic_order | `task_puzzles__cyclic_order__swap_repair_label` | ['bbox'] | 100 | 100 | 260 | 104 | 104 | pass |
| puzzles | matchstick | `task_puzzles__matchstick__matchstick_number_transform_label` | ['bbox_map'] | 100 | 200 | 320 | 218 | 218 | pass |
| puzzles | matchstick | `task_puzzles__matchstick__max_square_count_after_additions_value` | ['bbox_set'] | 100 | 352 | 144 | 144 | 144 | pass |
| puzzles | nonogram | `task_puzzles__nonogram__candidate_solution_label` | ['bbox'] | 100 | 100 | 112 | 136 | 112 | pass |
| puzzles | nonogram | `task_puzzles__nonogram__line_completion_label` | ['bbox'] | 100 | 100 | 112 | 92 | 92 | pass |
| puzzles | pipe_flow | `task_puzzles__pipe_flow__misrotated_tile_label` | ['bbox'] | 100 | 100 | 68 | 68 | 68 | pass |
| puzzles | pipe_flow | `task_puzzles__pipe_flow__pipe_flow_repair_tile_label` | ['bbox_map'] | 100 | 200 | 70 | 70 | 70 | pass |
| puzzles | polyomino_assembly | `task_puzzles__polyomino_assembly__composition_result_label` | ['bbox'] | 100 | 100 | 324 | 190 | 190 | pass |
| puzzles | polyomino_assembly | `task_puzzles__polyomino_assembly__decomposition_pair_label` | ['bbox'] | 100 | 100 | 324 | 190 | 190 | pass |
| puzzles | polyomino_assembly | `task_puzzles__polyomino_assembly__hole_fill_piece_label` | ['bbox'] | 100 | 100 | 324 | 190 | 190 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_analogical_transform_label` | ['bbox'] | 100 | 100 | 59 | 59 | 59 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_count_progression_label` | ['bbox'] | 100 | 100 | 60 | 60 | 60 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_feature_binding_label` | ['bbox'] | 100 | 100 | 59 | 59 | 59 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_position_progression_label` | ['bbox'] | 100 | 100 | 61 | 61 | 61 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_set_operation_label` | ['bbox'] | 100 | 100 | 60 | 60 | 60 | pass |
| puzzles | raven_matrix | `task_puzzles__raven_matrix__raven_spatial_transform_label` | ['bbox'] | 100 | 100 | 60 | 60 | 60 | pass |
| puzzles | rubiks_net | `task_puzzles__rubiks_net__post_move_face_color_count_label` | ['bbox'] | 100 | 100 | 136 | 154 | 136 | pass |
| puzzles | rubiks_net | `task_puzzles__rubiks_net__post_move_sticker_color_label` | ['bbox'] | 100 | 100 | 136 | 154 | 136 | pass |
| puzzles | rubiks_net | `task_puzzles__rubiks_net__rubiks_move_result_label` | ['bbox'] | 100 | 100 | 300 | 262 | 262 | pass |
| puzzles | sheet_transform | `task_puzzles__sheet_transform__fold_cut_result_label` | ['bbox'] | 100 | 100 | 121.499 | 121.499 | 121.499 | pass |
| puzzles | sheet_transform | `task_puzzles__sheet_transform__fold_projection_result_label` | ['bbox'] | 100 | 100 | 93 | 93 | 93 | pass |
| puzzles | sheet_transform | `task_puzzles__sheet_transform__overlay_union_result_label` | ['bbox'] | 100 | 100 | 150 | 150 | 150 | pass |
| puzzles | star_battle | `task_puzzles__star_battle__remaining_valid_cell_count` | ['bbox_set'] | 100 | 409 | 32 | 32 | 32 | pass |
| puzzles | star_battle | `task_puzzles__star_battle__valid_cell_anywhere_label` | ['bbox'] | 100 | 100 | 32 | 32 | 32 | pass |
| puzzles | sudoku | `task_puzzles__sudoku__marked_cell_candidate_count` | ['bbox'] | 100 | 100 | 36.556 | 36.556 | 36.556 | pass |
| puzzles | sudoku | `task_puzzles__sudoku__marked_cell_value` | ['bbox'] | 100 | 100 | 36.778 | 36.778 | 36.778 | pass |
| puzzles | sudoku | `task_puzzles__sudoku__mistake_cell_label` | ['bbox'] | 100 | 100 | 36.778 | 36.778 | 36.778 | pass |
| puzzles | tents | `task_puzzles__tents__missing_tent_cell_label` | ['bbox'] | 100 | 100 | 25 | 25 | 25 | pass |
| puzzles | tents | `task_puzzles__tents__violating_tent_label` | ['bbox'] | 100 | 100 | 36 | 36 | 36 | pass |
| puzzles | toggle_grid | `task_puzzles__toggle_grid__toggle_repair_switch_label` | ['bbox'] | 100 | 100 | 72 | 72 | 72 | pass |
| puzzles | toggle_grid | `task_puzzles__toggle_grid__toggle_result_label` | ['bbox'] | 100 | 100 | 230 | 178 | 178 | pass |
| puzzles | voxel_cube | `task_puzzles__voxel_cube__cube_count` | ['bbox'] | 100 | 100 | 120.64 | 96.72 | 96.72 | pass |
| puzzles | voxel_cube | `task_puzzles__voxel_cube__cube_projection_match_label` | ['bbox'] | 100 | 100 | 190 | 178 | 178 | pass |
| puzzles | voxel_cube | `task_puzzles__voxel_cube__cube_structure_change_count` | ['bbox_set'] | 100 | 200 | 60.32 | 63.44 | 60.32 | pass |
| puzzles | voxel_cube | `task_puzzles__voxel_cube__cube_visible_projection_count` | ['bbox_set'] | 100 | 503 | 40 | 40 | 40 | pass |
| puzzles | word_search | `task_puzzles__word_search__search_location_label` | ['bbox_sequence'] | 100 | 398 | 42 | 42 | 42 | pass |
