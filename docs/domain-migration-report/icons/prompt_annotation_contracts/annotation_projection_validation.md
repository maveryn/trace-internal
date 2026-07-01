# Annotation Projection Validation

- sampled instances: `76`
- query ids covered: `76`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 12, 'bbox_map': 11, 'bbox_set': 53}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_icons__icon_cutout__partial_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__icon_field__most_frequent_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__icon_field__singleton_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__mirror_grid__mirror_symmetry_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__closer_to_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__counterfactual_attribute_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__counterfactual_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_and_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_complement_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_exclusion_count | `color_and_not_shape_count, shape_and_not_color_count` | `{'color_and_not_shape_count': 1, 'shape_and_not_color_count': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_or_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_xor_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__reference_distance_rank_label | `closest_to_named_reference_label, farthest_from_named_reference_label, second_closest_to_named_reference_label` | `{'closest_to_named_reference_label': 1, 'farthest_from_named_reference_label': 1, 'second_closest_to_named_reference_label': 1}` | 3 | `` |
| task_icons__named_field__scoped_attribute_count | `inside_band_count, inside_quadrant_count, inside_shape_count, inside_shelf_count, outside_band_count, outside_shape_count` | `{'inside_band_count': 1, 'inside_quadrant_count': 1, 'inside_shape_count': 1, 'inside_shelf_count': 1, 'outside_band_count': 1, 'outside_shape_count': 1}` | 6 | `` |
| task_icons__named_field__single_attribute_membership_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_grid__group_predicate_count | `column_at_least_shape_count, column_exactly_shape_count, column_no_shape_count, row_at_least_shape_count, row_exactly_shape_count, row_no_shape_count` | `{'column_at_least_shape_count': 1, 'column_exactly_shape_count': 1, 'column_no_shape_count': 1, 'row_at_least_shape_count': 1, 'row_exactly_shape_count': 1, 'row_no_shape_count': 1}` | 6 | `` |
| task_icons__named_grid__row_column_shape_extreme_number | `column_fewest_shape_number, column_most_shape_number, row_fewest_shape_number, row_most_shape_number` | `{'column_fewest_shape_number': 1, 'column_most_shape_number': 1, 'row_fewest_shape_number': 1, 'row_most_shape_number': 1}` | 4 | `` |
| task_icons__named_grid__scoped_attribute_count | `column_shape_count, row_shape_count` | `{'column_shape_count': 1, 'row_shape_count': 1}` | 2 | `` |
| task_icons__named_path__path_neighbor_label | `after_first_shape_label, after_last_shape_label, after_second_shape_label, before_first_shape_label, before_last_shape_label, before_second_shape_label` | `{'after_first_shape_label': 1, 'after_last_shape_label': 1, 'after_second_shape_label': 1, 'before_first_shape_label': 1, 'before_last_shape_label': 1, 'before_second_shape_label': 1}` | 6 | `` |
| task_icons__named_ring__scoped_attribute_count | `clockwise_arc_shape_count, counterclockwise_arc_shape_count` | `{'clockwise_arc_shape_count': 1, 'counterclockwise_arc_shape_count': 1}` | 2 | `` |
| task_icons__named_strip__shape_run_length | `longest_shape_run_length, shortest_shape_run_length` | `{'longest_shape_run_length': 1, 'shortest_shape_run_length': 1}` | 2 | `` |
| task_icons__overlap_grid__occlusion_order_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__pair_grid__reference_color_pair_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__pair_grid__reference_transform_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__paired_canvas__color_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__paired_canvas__panel_set_relation_count | `added_in_right_count, missing_from_right_count` | `{'added_in_right_count': 1, 'missing_from_right_count': 1}` | 2 | `` |
| task_icons__paired_canvas__rotation_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__anchor_position_count | `above_anchor, below_anchor, left_of_anchor, right_of_anchor` | `{'above_anchor': 1, 'below_anchor': 1, 'left_of_anchor': 1, 'right_of_anchor': 1}` | 4 | `` |
| task_icons__reference_canvas__reference_color_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_metric_relation_count | `size_larger, size_smaller` | `{'size_larger': 1, 'size_smaller': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_rotation_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_type_color_rotation_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_type_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__count_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__rotation_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__size_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__single_transform_options__geometric_transform_result_label | `flip_horizontal_result_label, flip_vertical_result_label, rotate_180_result_label, rotate_90_clockwise_result_label, rotate_90_counterclockwise_result_label` | `{'flip_horizontal_result_label': 1, 'flip_vertical_result_label': 1, 'rotate_180_result_label': 1, 'rotate_90_clockwise_result_label': 1, 'rotate_90_counterclockwise_result_label': 1}` | 5 | `` |
| task_icons__venn_field__scoped_attribute_count | `inside_both_circles_count, inside_either_circle_count, inside_exactly_one_circle_count, outside_both_circles_count` | `{'inside_both_circles_count': 1, 'inside_either_circle_count': 1, 'inside_exactly_one_circle_count': 1, 'outside_both_circles_count': 1}` | 4 | `` |
| task_icons__wallpaper_panels__motif_violation_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__wallpaper_panels__same_pattern_as_reference_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
