# Annotation Projection Validation

- sampled instances: `65`
- query ids covered: `65`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 47, 'bbox_map': 3, 'bbox_sequence': 1, 'bbox_set': 8, 'point': 2, 'segment': 2, 'segment_set': 2}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
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
| task_puzzles__polyomino_assembly__hole_fill_piece_label | `single` | `{'single': 1}` | 2 | `` |
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
| task_puzzles__voxel_cube__cube_projection_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_structure_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__voxel_cube__cube_visible_projection_count | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__word_search__present_word_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_puzzles__word_search__search_location_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
