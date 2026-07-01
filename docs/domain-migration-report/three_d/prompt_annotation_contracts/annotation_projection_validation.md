# Annotation Projection Validation

- sampled instances: `79`
- query ids covered: `79`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 27, 'bbox_set': 28, 'bbox_set_map': 12, 'point': 7, 'point_map': 1, 'segment_set': 4}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_three_d__carousel__belt_object_type_count_arithmetic_value | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__carousel__belt_total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__between_object_type_anchors_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__color_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__color_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__object_type_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__object_type_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_belt_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_belt_object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_color_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__belt_total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__between_object_type_anchors_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__color_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__color_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__lane_object_type_count_arithmetic_value | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__conveyor__object_type_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__object_type_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_belt_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_belt_object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_color_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__color_count_arithmetic | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__object_cluster__color_membership_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__counterfactual_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_and_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_exclusion_count | `color_and_not_type_count, type_and_not_color_count` | `{'color_and_not_type_count': 1, 'type_and_not_color_count': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_or_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_xor_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__object_type_count_arithmetic | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__object_cluster__total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__between_references_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__camera_depth_relation_count | `closer_to_camera_than_reference_count, farther_from_camera_than_reference_count` | `{'closer_to_camera_than_reference_count': 1, 'farther_from_camera_than_reference_count': 1}` | 2 | `` |
| task_three_d__object_scene__camera_distance_extremum_label | `closest_to_camera, farthest_from_camera` | `{'closest_to_camera': 1, 'farthest_from_camera': 1}` | 2 | `` |
| task_three_d__object_scene__height_extremum_label | `highest_above_floor, lowest_above_floor` | `{'highest_above_floor': 1, 'lowest_above_floor': 1}` | 2 | `` |
| task_three_d__object_scene__image_plane_lateral_relation_count | `left_of_reference_in_view_count, right_of_reference_in_view_count` | `{'left_of_reference_in_view_count': 1, 'right_of_reference_in_view_count': 1}` | 2 | `` |
| task_three_d__object_scene__line_side_label | `left_of_directed_line, right_of_directed_line` | `{'left_of_directed_line': 1, 'right_of_directed_line': 1}` | 2 | `` |
| task_three_d__object_scene__marked_point_depth_extremum_label | `closest_marked_point, farthest_marked_point` | `{'closest_marked_point': 1, 'farthest_marked_point': 1}` | 2 | `` |
| task_three_d__object_scene__marked_point_vertical_relation_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__multiview_object_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__object_relation_label | `inside_prop, on_top_of_prop, under_prop` | `{'inside_prop': 1, 'on_top_of_prop': 1, 'under_prop': 1}` | 3 | `` |
| task_three_d__object_scene__occlusion_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__point_camera_distance_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__point_on_object_line_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__reference_nearest_label | `closest_to_reference, farthest_from_reference` | `{'closest_to_reference': 1, 'farthest_from_reference': 1}` | 2 | `` |
| task_three_d__object_scene__reference_triangle_inside_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_camera_distance_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_same_wall_reference_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_side_relation_label | `left_of_reference_on_wall, right_of_reference_on_wall` | `{'left_of_reference_on_wall': 1, 'right_of_reference_on_wall': 1}` | 2 | `` |
| task_three_d__street__intersection_nearest_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__street__lane_ahead_object_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__street__same_road_arm_reference_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__color_count_after_operations_value | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__color_frequency_option_label | `absent_color, most_frequent_color` | `{'absent_color': 1, 'most_frequent_color': 1}` | 2 | `` |
| task_three_d__surface_fixture__colored_element_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__element_count_extremum_label | `highest_element_count, lowest_element_count` | `{'highest_element_count': 1, 'lowest_element_count': 1}` | 2 | `` |
| task_three_d__surface_fixture__recolor_board_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__repeated_element_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__scoped_colored_element_count | `column_scoped_color_count, row_scoped_color_count` | `{'column_scoped_color_count': 1, 'row_scoped_color_count': 1}` | 2 | `` |
| task_three_d__warehouse__nearest_candidate_to_reference_label | `closest_object_to_reference, closest_object_to_robot` | `{'closest_object_to_reference': 1, 'closest_object_to_robot': 1}` | 2 | `` |
| task_three_d__warehouse__robot_forward_path_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
