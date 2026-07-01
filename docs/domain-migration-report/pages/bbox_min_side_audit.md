# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-07-01T10:10:38Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `25`
- Tasks: `80`
- Bbox-family runtime tasks: `77`
- Samples inspected: `8200`
- Bboxes inspected: `21052`
- Failing bbox tasks: `17`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Attention Needed

- FAIL `pages/calendar_event_grid/task_pages__calendar_event_grid__category_slot_day_count`: min_side=`13.866` failures=`394`
- FAIL `pages/calendar_event_grid/task_pages__calendar_event_grid__date_filled_slot_count`: min_side=`13.866` failures=`152`
- FAIL `pages/calendar_event_grid/task_pages__calendar_event_grid__date_for_category_slot_label`: min_side=`13.867` failures=`100`
- FAIL `pages/calendar_event_grid/task_pages__calendar_event_grid__date_slot_category_label`: min_side=`13.867` failures=`100`
- FAIL `pages/category_grid/task_pages__category_grid__category_item_count`: min_side=`8.422` failures=`250`
- FAIL `pages/category_grid/task_pages__category_grid__category_slot_item_label`: min_side=`8.5` failures=`254`
- FAIL `pages/mixed_infographic_page/task_pages__mixed_infographic_page__module_condition_item_count`: min_side=`10.518` failures=`94`
- FAIL `pages/mixed_infographic_page/task_pages__mixed_infographic_page__module_field_ranked_item_label`: min_side=`9` failures=`100`
- FAIL `pages/mixed_infographic_page/task_pages__mixed_infographic_page__module_field_total_value`: min_side=`3.222` failures=`116`
- FAIL `pages/mixed_infographic_page/task_pages__mixed_infographic_page__module_field_value_label`: min_side=`8` failures=`35`
- FAIL `pages/mixed_infographic_page/task_pages__mixed_infographic_page__module_two_field_condition_item_label`: min_side=`10` failures=`100`
- FAIL `pages/profile_card_grid/task_pages__profile_card_grid__value_for_named_profile_field`: min_side=`6` failures=`100`
- FAIL `pages/sectioned_infographic/task_pages__sectioned_infographic__section_filtered_item_label`: min_side=`14` failures=`13`
- FAIL `pages/sectioned_infographic/task_pages__sectioned_infographic__section_item_count`: min_side=`15` failures=`80`
- FAIL `pages/step_list/task_pages__step_list__nth_step_field_label`: min_side=`9` failures=`99`
- FAIL `pages/step_list/task_pages__step_list__step_after_named_step_label`: min_side=`13` failures=`99`
- FAIL `pages/step_list/task_pages__step_list__step_for_detail_label`: min_side=`13` failures=`50`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| pages | calendar | `task_pages__calendar__date_range_day_class_count` | ['bbox_set'] | 100 | 448 | 69.679 | 56.732 | 56.732 | pass |
| pages | calendar | `task_pages__calendar__date_weekday_label` | ['bbox'] | 100 | 100 | 69.506 | 53.743 | 53.743 | pass |
| pages | calendar | `task_pages__calendar__marked_day_class_count` | ['bbox_set'] | 100 | 255 | 69.955 | 58.042 | 58.042 | pass |
| pages | calendar | `task_pages__calendar__weekday_occurrence_date` | ['bbox'] | 100 | 100 | 69.661 | 50.207 | 50.207 | pass |
| pages | calendar | `task_pages__calendar__workday_offset_date` | ['bbox_map'] | 100 | 200 | 69.625 | 50.998 | 50.998 | pass |
| pages | calendar_event_grid | `task_pages__calendar_event_grid__category_slot_day_count` | ['bbox_set'] | 100 | 394 | 89.2 | 13.866 | 13.866 | fail |
| pages | calendar_event_grid | `task_pages__calendar_event_grid__date_filled_slot_count` | ['bbox_set'] | 100 | 152 | 89.2 | 13.866 | 13.866 | fail |
| pages | calendar_event_grid | `task_pages__calendar_event_grid__date_for_category_slot_label` | ['bbox'] | 100 | 100 | 89.2 | 13.867 | 13.867 | fail |
| pages | calendar_event_grid | `task_pages__calendar_event_grid__date_slot_category_label` | ['bbox'] | 100 | 100 | 89.2 | 13.867 | 13.867 | fail |
| pages | category_grid | `task_pages__category_grid__category_item_count` | ['bbox_set'] | 100 | 414 | 208.5 | 8.422 | 8.422 | fail |
| pages | category_grid | `task_pages__category_grid__category_slot_item_label` | ['bbox_map'] | 100 | 300 | 28 | 8.5 | 8.5 | fail |
| pages | concept_map | `task_pages__concept_map__branch_child_count` | ['bbox_set'] | 100 | 452 | 128 | 34 | 34 | pass |
| pages | concept_map | `task_pages__concept_map__marked_child_count` | ['bbox_set'] | 100 | 275 | 128 | 34 | 34 | pass |
| pages | concept_map | `task_pages__concept_map__ordered_child_label` | ['bbox'] | 100 | 100 | 128 | 34 | 34 | pass |
| pages | control_board | `task_pages__control_board__control_state_condition_count` | ['bbox_set'] | 100 | 462 | 121.25 | 82 | 82 | pass |
| pages | cycle | `task_pages__cycle__offset_stage_label` | ['bbox'] | 100 | 100 | 122 | 58 | 58 | pass |
| pages | form_section | `task_pages__form_section__sum_minus_amount_in_section_value` | ['bbox_map'] | 100 | 300 | 424 | 42.125 | 42.125 | pass |
| pages | form_section | `task_pages__form_section__two_amount_arithmetic_value` | ['bbox_map'] | 100 | 200 | 424 | 42.125 | 42.125 | pass |
| pages | hero_callout_infographic | `task_pages__hero_callout_infographic__callout_condition_count` | ['bbox_set'] | 100 | 285 | 253.6 | 25.67 | 25.67 | pass |
| pages | hero_callout_infographic | `task_pages__hero_callout_infographic__callout_field_value_label` | ['bbox_map'] | 100 | 200 | 253.6 | 25.67 | 25.67 | pass |
| pages | hero_callout_infographic | `task_pages__hero_callout_infographic__callout_metric_extremum_label` | ['bbox_map'] | 100 | 568 | 253.6 | 25.67 | 25.67 | pass |
| pages | hierarchy | `task_pages__hierarchy__manager_most_direct_reports_label` | ['bbox'] | 100 | 100 | 84 | 48 | 48 | pass |
| pages | hierarchy | `task_pages__hierarchy__manager_most_total_reports_label` | ['bbox'] | 100 | 100 | 84 | 48 | 48 | pass |
| pages | hierarchy | `task_pages__hierarchy__subtree_descendant_count` | ['bbox_set'] | 100 | 1021 | 84 | 48 | 48 | pass |
| pages | infographic | `task_pages__infographic__global_metric_ranked_item_label` | ['bbox'] | 100 | 100 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__metric_card_field_lookup` | ['bbox'] | 100 | 100 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_extrema_arithmetic_value` | ['bbox_map'] | 100 | 200 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_icon_extremum_label` | ['bbox'] | 100 | 100 | 376 | 160 | 160 | pass |
| pages | infographic | `task_pages__infographic__section_icon_total_difference_value` | ['bbox_set_map'] | 100 | 242 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_icon_total_value` | ['bbox_set'] | 100 | 209 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_metric_ranked_item_label` | ['bbox'] | 100 | 100 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_ranked_total_label` | ['bbox_set'] | 100 | 502 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_total_except_named_value` | ['bbox_set'] | 100 | 360 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__section_total_extrema_difference_value` | ['bbox_set_map'] | 100 | 999 | 116 | 86 | 86 | pass |
| pages | infographic | `task_pages__infographic__sum_named_metrics_value` | ['bbox_set'] | 100 | 494 | 116 | 86 | 86 | pass |
| pages | instruction_panel | `task_pages__instruction_panel__shared_control_for_step_set_label` | ['bbox_set'] | 100 | 245 | 118 | 30 | 30 | pass |
| pages | instruction_panel | `task_pages__instruction_panel__step_for_control_pair_label` | ['bbox_set'] | 100 | 300 | 34 | 30 | 30 | pass |
| pages | map | `task_pages__map__destination_after_directions_label` | ['bbox_sequence'] | 100 | 389 | 126 | 58 | 58 | pass |
| pages | map | `task_pages__map__landmark_after_route_step_label` | ['bbox_sequence'] | 100 | 392 | 126 | 58 | 58 | pass |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__module_condition_item_count` | ['bbox_set'] | 100 | 334 | 32.965 | 10.518 | 10.518 | fail |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__module_field_ranked_item_label` | ['bbox'] | 100 | 100 | 15 | 9 | 9 | fail |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__module_field_total_value` | ['bbox_set'] | 100 | 288 | 34 | 3.222 | 3.222 | fail |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__module_field_value_label` | ['bbox'] | 100 | 100 | 37.912 | 8 | 8 | fail |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__module_two_field_condition_item_label` | ['bbox'] | 100 | 100 | 25 | 10 | 10 | fail |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__page_field_extremum_module_label` | ['bbox'] | 100 | 100 | 208.313 | 142 | 142 | pass |
| pages | mixed_infographic_page | `task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label` | ['bbox'] | 100 | 100 | 190.672 | 162.232 | 162.232 | pass |
| pages | navigation_flow | `task_pages__navigation_flow__navigation_path_target_label` | ['bbox'] | 100 | 100 | 63.333 | 39 | 39 | pass |
| pages | navigation_flow | `task_pages__navigation_flow__same_group_target_label` | ['bbox'] | 100 | 100 | 72 | 24 | 24 | pass |
| pages | paired_forms | `task_pages__paired_forms__shortfall_minus_overage_value` | ['bbox_set'] | 100 | 384 | 602 | 50 | 50 | pass |
| pages | paired_forms | `task_pages__paired_forms__sum_absolute_quantity_differences_value` | ['bbox_set'] | 100 | 397 | 602 | 50 | 50 | pass |
| pages | paired_forms | `task_pages__paired_forms__total_amount_delta_value` | ['bbox_set'] | 100 | 404 | 602 | 50 | 50 | pass |
| pages | process_flow | `task_pages__process_flow__condition_path_endpoint_label` | ['bbox_map'] | 100 | 400 | 46 | 24 | 24 | pass |
| pages | process_flow | `task_pages__process_flow__filtered_node_count` | ['bbox_set'] | 100 | 519 | 87.48 | 64 | 64 | pass |
| pages | profile_card_grid | `task_pages__profile_card_grid__field_ranked_profile_label` | ['bbox'] | 100 | 100 | 341.333 | 129.6 | 129.6 | pass |
| pages | profile_card_grid | `task_pages__profile_card_grid__profile_for_field_value` | ['bbox'] | 100 | 100 | 341.333 | 129.6 | 129.6 | pass |
| pages | profile_card_grid | `task_pages__profile_card_grid__value_for_named_profile_field` | ['bbox'] | 100 | 100 | 19 | 6 | 6 | fail |
| pages | record_table | `task_pages__record_table__enabled_action_for_type_count` | ['bbox_set'] | 100 | 402 | 1116 | 28 | 28 | pass |
| pages | record_table | `task_pages__record_table__selected_rows_with_status_count` | ['bbox_set'] | 100 | 418 | 1116 | 28 | 28 | pass |
| pages | record_table | `task_pages__record_table__value_threshold_in_group_count` | ['bbox_set'] | 100 | 462 | 1116 | 28 | 28 | pass |
| pages | schedule | `task_pages__schedule__longer_than_reference_count` | ['bbox_set'] | 100 | 215 | 137.2 | 92.1 | 92.1 | pass |
| pages | schedule | `task_pages__schedule__maximum_non_overlapping_count` | ['bbox_set'] | 100 | 362 | 137.2 | 30.7 | 30.7 | pass |
| pages | schedule | `task_pages__schedule__overlap_count` | ['bbox_set'] | 100 | 304 | 173.5 | 30.7 | 30.7 | pass |
| pages | schema | `task_pages__schema__field_role_count` | ['bbox_set'] | 100 | 516 | 188 | 24 | 24 | pass |
| pages | schema | `task_pages__schema__relationship_cardinality_label` | ['bbox_map'] | 300 | 600 | 24 | 24 | 24 | pass |
| pages | schema | `task_pages__schema__relationship_endpoint_label` | ['bbox'] | 100 | 100 | 188 | 106 | 106 | pass |
| pages | sectioned_infographic | `task_pages__sectioned_infographic__section_filtered_item_label` | ['bbox'] | 100 | 100 | 277.333 | 14 | 14 | fail |
| pages | sectioned_infographic | `task_pages__sectioned_infographic__section_item_count` | ['bbox_set'] | 100 | 480 | 277.333 | 15 | 15 | fail |
| pages | step_list | `task_pages__step_list__nth_step_field_label` | ['bbox'] | 100 | 100 | 27 | 9 | 9 | fail |
| pages | step_list | `task_pages__step_list__step_after_named_step_label` | ['bbox'] | 100 | 100 | 30 | 13 | 13 | fail |
| pages | step_list | `task_pages__step_list__step_for_detail_label` | ['bbox'] | 100 | 100 | 26 | 13 | 13 | fail |
| pages | timeline | `task_pages__timeline__event_date_gap_value` | ['bbox_map'] | 100 | 200 | 72 | 70 | 70 | pass |
| pages | timeline | `task_pages__timeline__interval_membership_count` | ['bbox_set'] | 100 | 393 | 72 | 70 | 70 | pass |
| pages | web_action | `task_pages__web_action__action_target_label` | ['bbox'] | 100 | 100 | 126 | 24 | 24 | pass |
| pages | web_action | `task_pages__web_action__guide_code_target_count` | ['bbox_set'] | 100 | 450 | 126 | 24 | 24 | pass |
| pages | workspace | `task_pages__workspace__context_control_count` | ['bbox_set'] | 100 | 266 | 148.4 | 52 | 52 | pass |
| pages | workspace | `task_pages__workspace__control_label` | ['bbox'] | 100 | 100 | 148.4 | 52 | 52 | pass |
| pages | workspace | `task_pages__workspace__dual_guide_control_label` | ['bbox'] | 100 | 100 | 148.4 | 41.2 | 41.2 | pass |
