# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-28T10:41:04Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `8`
- Tasks: `60`
- Bbox-family runtime tasks: `50`
- Samples inspected: `6000`
- Bboxes inspected: `18417`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| three_d | carousel | `task_three_d__carousel__belt_object_type_count_arithmetic_value` | ['bbox_set_map'] | 100 | 640 | 25.048 | 24.236 | 24.236 | pass |
| three_d | carousel | `task_three_d__carousel__belt_total_object_count` | ['bbox_set'] | 100 | 500 | 27.26 | 24.323 | 24.323 | pass |
| three_d | carousel | `task_three_d__carousel__between_object_type_anchors_count` | ['bbox_set'] | 100 | 284 | 32.799 | 24.005 | 24.005 | pass |
| three_d | carousel | `task_three_d__carousel__color_transfer_total_count` | ['bbox_set_map'] | 100 | 628 | 33.639 | 24.265 | 24.265 | pass |
| three_d | carousel | `task_three_d__carousel__object_type_transfer_total_count` | ['bbox_set_map'] | 100 | 589 | 35.334 | 24.051 | 24.051 | pass |
| three_d | carousel | `task_three_d__carousel__scoped_belt_color_count` | ['bbox_set'] | 100 | 261 | 34.527 | 24.54 | 24.54 | pass |
| three_d | carousel | `task_three_d__carousel__scoped_belt_object_type_count` | ['bbox_set'] | 100 | 260 | 28.881 | 24.298 | 24.298 | pass |
| three_d | carousel | `task_three_d__carousel__scoped_color_type_count` | ['bbox_set'] | 100 | 247 | 33.537 | 24.842 | 24.842 | pass |
| three_d | conveyor | `task_three_d__conveyor__belt_total_object_count` | ['bbox_set'] | 100 | 425 | 36 | 24.284 | 24.284 | pass |
| three_d | conveyor | `task_three_d__conveyor__between_object_type_anchors_count` | ['bbox_set'] | 100 | 295 | 24.694 | 24.173 | 24.173 | pass |
| three_d | conveyor | `task_three_d__conveyor__color_transfer_total_count` | ['bbox_set_map'] | 100 | 708 | 36 | 24.094 | 24.094 | pass |
| three_d | conveyor | `task_three_d__conveyor__lane_object_type_count_arithmetic_value` | ['bbox_set_map'] | 100 | 758 | 24.108 | 24.131 | 24.108 | pass |
| three_d | conveyor | `task_three_d__conveyor__object_type_transfer_total_count` | ['bbox_set_map'] | 100 | 679 | 36 | 24.067 | 24.067 | pass |
| three_d | conveyor | `task_three_d__conveyor__scoped_belt_color_count` | ['bbox_set'] | 100 | 263 | 36 | 24.403 | 24.403 | pass |
| three_d | conveyor | `task_three_d__conveyor__scoped_belt_object_type_count` | ['bbox_set'] | 100 | 310 | 27.609 | 24.132 | 24.132 | pass |
| three_d | conveyor | `task_three_d__conveyor__scoped_color_type_count` | ['bbox_set'] | 100 | 257 | 38.527 | 24.515 | 24.515 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__color_count_arithmetic` | ['bbox_set_map'] | 100 | 695 | 24.473 | 24.659 | 24.473 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__color_membership_count` | ['bbox_set'] | 100 | 540 | 24.978 | 24.324 | 24.324 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__counterfactual_count` | ['bbox_set'] | 100 | 505 | 24.49 | 24.862 | 24.49 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__multi_attribute_and_count` | ['bbox_set'] | 100 | 352 | 24.329 | 24.735 | 24.329 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__multi_attribute_exclusion_count` | ['bbox_set'] | 100 | 312 | 26.098 | 25.014 | 25.014 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__multi_attribute_or_count` | ['bbox_set'] | 100 | 567 | 25.427 | 25.467 | 25.427 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__multi_attribute_xor_count` | ['bbox_set'] | 100 | 350 | 24.69 | 24.246 | 24.246 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__object_type_count` | ['bbox_set'] | 100 | 610 | 32.314 | 24.556 | 24.556 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__object_type_count_arithmetic` | ['bbox_set_map'] | 100 | 737 | 24.36 | 24.885 | 24.36 | pass |
| three_d | object_cluster | `task_three_d__object_cluster__total_object_count` | ['bbox_set'] | 100 | 1169 | 25.516 | 26.059 | 25.516 | pass |
| three_d | object_scene | `task_three_d__object_scene__between_references_label` | ['bbox'] | 100 | 100 | 24 | 29.177 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__camera_depth_relation_count` | ['bbox_set'] | 100 | 337 | 24 | 25.926 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__camera_distance_extremum_label` | ['bbox'] | 100 | 100 | 24 | 26.193 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__height_extremum_label` | ['bbox'] | 100 | 100 | 29.111 | 36 | 29.111 | pass |
| three_d | object_scene | `task_three_d__object_scene__image_plane_lateral_relation_count` | ['bbox_set'] | 100 | 336 | 24 | 26.282 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__multiview_object_match_label` | ['bbox'] | 100 | 100 | 24.003 | 30.29 | 24.003 | pass |
| three_d | object_scene | `task_three_d__object_scene__object_relation_label` | ['bbox'] | 100 | 100 | 24 | 24 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__occlusion_order_label` | ['bbox'] | 100 | 100 | 24 | 48.849 | 24 | pass |
| three_d | object_scene | `task_three_d__object_scene__reference_nearest_label` | ['bbox'] | 100 | 100 | 35.094 | 32.209 | 32.209 | pass |
| three_d | room | `task_three_d__room__wall_object_camera_distance_label` | ['bbox'] | 100 | 100 | 48.728 | 81.579 | 48.728 | pass |
| three_d | room | `task_three_d__room__wall_object_same_wall_reference_label` | ['bbox'] | 100 | 100 | 27.203 | 48.079 | 27.203 | pass |
| three_d | room | `task_three_d__room__wall_object_side_relation_label` | ['bbox'] | 100 | 100 | 29.652 | 34.129 | 29.652 | pass |
| three_d | street | `task_three_d__street__intersection_nearest_label` | ['bbox'] | 100 | 100 | 24.431 | 26.405 | 24.431 | pass |
| three_d | street | `task_three_d__street__lane_ahead_object_label` | ['bbox'] | 100 | 100 | 24.431 | 24.175 | 24.175 | pass |
| three_d | street | `task_three_d__street__same_road_arm_reference_label` | ['bbox'] | 100 | 100 | 24.622 | 24.972 | 24.622 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__color_count_after_operations_value` | ['bbox_set'] | 100 | 370 | 59.764 | 68.011 | 59.764 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__color_frequency_option_label` | ['bbox'] | 100 | 100 | 229 | 90 | 90 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__colored_element_count` | ['bbox_set'] | 100 | 695 | 49.253 | 48.613 | 48.613 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__element_count_extremum_label` | ['bbox'] | 100 | 100 | 403 | 404 | 403 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__recolor_board_match_label` | ['bbox'] | 100 | 100 | 404 | 277 | 277 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__repeated_element_count` | ['bbox_set'] | 100 | 1620 | 26 | 24 | 24 | pass |
| three_d | surface_fixture | `task_three_d__surface_fixture__scoped_colored_element_count` | ['bbox_set'] | 100 | 318 | 49.618 | 45.202 | 45.202 | pass |
| three_d | warehouse | `task_three_d__warehouse__nearest_candidate_to_reference_label` | ['bbox'] | 100 | 100 | 30.048 | 36.458 | 30.048 | pass |
| three_d | warehouse | `task_three_d__warehouse__robot_forward_path_label` | ['bbox'] | 100 | 100 | 30.203 | 39.947 | 30.203 | pass |
