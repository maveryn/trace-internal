# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-28T07:22:58Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `16`
- Tasks: `40`
- Bbox-family runtime tasks: `40`
- Samples inspected: `3820`
- Bboxes inspected: `10005`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| icons | icon_cutout | `task_icons__icon_cutout__partial_match_label` | ['bbox_map'] | 100 | 200 | 87 | 103 | 87 | pass |
| icons | icon_field | `task_icons__icon_field__most_frequent_type_count` | ['bbox_set'] | 100 | 399 | 35 | 39 | 35 | pass |
| icons | icon_field | `task_icons__icon_field__singleton_type_count` | ['bbox_set'] | 100 | 213 | 32 | 36 | 32 | pass |
| icons | mirror_grid | `task_icons__mirror_grid__mirror_symmetry_match_label` | ['bbox_map'] | 100 | 200 | 212 | 212 | 212 | pass |
| icons | named_field | `task_icons__named_field__closer_to_reference_count` | ['bbox_set'] | 100 | 169 | 24 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__counterfactual_attribute_count` | ['bbox_set'] | 100 | 479 | 24 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__counterfactual_total_count` | ['bbox_set'] | 100 | 449 | 24 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__multi_attribute_and_count` | ['bbox_set'] | 100 | 310 | 24 | 25 | 24 | pass |
| icons | named_field | `task_icons__named_field__multi_attribute_complement_count` | ['bbox_set'] | 100 | 280 | 24 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__multi_attribute_exclusion_count` | ['bbox_set'] | 100 | 319 | 29 | 25 | 25 | pass |
| icons | named_field | `task_icons__named_field__multi_attribute_or_count` | ['bbox_set'] | 100 | 288 | 25 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__multi_attribute_xor_count` | ['bbox_set'] | 100 | 312 | 24 | 24 | 24 | pass |
| icons | named_field | `task_icons__named_field__reference_distance_rank_label` | ['bbox_map'] | 100 | 200 | 27 | 28 | 27 | pass |
| icons | named_field | `task_icons__named_field__scoped_attribute_count` | ['bbox_set'] | 100 | 285 | 24 | 26 | 24 | pass |
| icons | named_field | `task_icons__named_field__single_attribute_membership_count` | ['bbox_set'] | 100 | 417 | 28 | 24 | 24 | pass |
| icons | named_grid | `task_icons__named_grid__group_predicate_count` | ['bbox_set'] | 60 | 149 | 90 | 90 | 90 | pass |
| icons | named_grid | `task_icons__named_grid__row_column_shape_extreme_number` | ['bbox_set'] | 40 | 110 | 29 | 24 | 24 | pass |
| icons | named_grid | `task_icons__named_grid__scoped_attribute_count` | ['bbox_set'] | 20 | 53 | 26 | 28 | 26 | pass |
| icons | named_path | `task_icons__named_path__path_neighbor_label` | ['bbox'] | 100 | 100 | 24 | 29 | 24 | pass |
| icons | named_ring | `task_icons__named_ring__scoped_attribute_count` | ['bbox_set'] | 100 | 298 | 24 | 24 | 24 | pass |
| icons | named_strip | `task_icons__named_strip__shape_run_length` | ['bbox_set'] | 100 | 350 | 24 | 24 | 24 | pass |
| icons | overlap_grid | `task_icons__overlap_grid__occlusion_order_count` | ['bbox_set'] | 100 | 186 | 154 | 239 | 154 | pass |
| icons | pair_grid | `task_icons__pair_grid__reference_color_pair_match_label` | ['bbox'] | 100 | 100 | 212 | 239 | 212 | pass |
| icons | pair_grid | `task_icons__pair_grid__reference_transform_match_label` | ['bbox'] | 100 | 100 | 328 | 239 | 239 | pass |
| icons | paired_canvas | `task_icons__paired_canvas__color_change_count` | ['bbox_set'] | 100 | 290 | 24 | 24 | 24 | pass |
| icons | paired_canvas | `task_icons__paired_canvas__panel_set_relation_count` | ['bbox_set'] | 100 | 296 | 24 | 24 | 24 | pass |
| icons | paired_canvas | `task_icons__paired_canvas__rotation_change_count` | ['bbox_set'] | 100 | 297 | 24 | 26 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__anchor_position_count` | ['bbox_set'] | 100 | 242 | 24 | 24 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__reference_color_match_count` | ['bbox_set'] | 100 | 377 | 24 | 26 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__reference_metric_relation_count` | ['bbox_set'] | 100 | 296 | 24 | 24 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__reference_rotation_match_count` | ['bbox_set'] | 100 | 361 | 24 | 24 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__reference_type_color_rotation_match_count` | ['bbox_set'] | 100 | 402 | 24 | 24 | 24 | pass |
| icons | reference_canvas | `task_icons__reference_canvas__reference_type_match_count` | ['bbox_set'] | 100 | 419 | 24 | 24 | 24 | pass |
| icons | sequence_strip | `task_icons__sequence_strip__count_progression_completion_label` | ['bbox'] | 100 | 100 | 132 | 136 | 132 | pass |
| icons | sequence_strip | `task_icons__sequence_strip__rotation_progression_completion_label` | ['bbox'] | 100 | 100 | 132 | 136 | 132 | pass |
| icons | sequence_strip | `task_icons__sequence_strip__size_progression_completion_label` | ['bbox'] | 100 | 100 | 132 | 136 | 132 | pass |
| icons | single_transform_options | `task_icons__single_transform_options__geometric_transform_result_label` | ['bbox_map'] | 100 | 200 | 50 | 60 | 50 | pass |
| icons | venn_field | `task_icons__venn_field__scoped_attribute_count` | ['bbox_set'] | 100 | 259 | 24 | 24 | 24 | pass |
| icons | wallpaper_panels | `task_icons__wallpaper_panels__motif_violation_label` | ['bbox'] | 100 | 100 | 510 | 278 | 278 | pass |
| icons | wallpaper_panels | `task_icons__wallpaper_panels__same_pattern_as_reference_label` | ['bbox_map'] | 100 | 200 | 510 | 286 | 286 | pass |
