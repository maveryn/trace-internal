# Annotation Projection Validation

- sampled instances: `107`
- query ids covered: `107`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 44, 'bbox_map': 13, 'bbox_sequence': 2, 'bbox_set': 42, 'bbox_set_map': 2, 'segment_set': 4}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_pages__calendar__date_range_day_class_count | `weekday_range_count, weekend_range_count` | `{'weekday_range_count': 1, 'weekend_range_count': 1}` | 2 | `` |
| task_pages__calendar__date_weekday_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__marked_day_class_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__weekday_occurrence_date | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__workday_offset_date | `workday_after_offset_date, workday_before_offset_date` | `{'workday_after_offset_date': 1, 'workday_before_offset_date': 1}` | 2 | `` |
| task_pages__calendar_event_grid__category_slot_day_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_filled_slot_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_for_category_slot_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_slot_category_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__category_grid__category_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__category_grid__category_slot_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__branch_child_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__marked_child_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__ordered_child_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__control_board__control_state_condition_count | `disabled_controls_in_group_count, selected_enabled_controls_in_group_count` | `{'disabled_controls_in_group_count': 1, 'selected_enabled_controls_in_group_count': 1}` | 2 | `` |
| task_pages__cycle__offset_stage_label | `after_stage_offset_label, before_stage_offset_label` | `{'after_stage_offset_label': 1, 'before_stage_offset_label': 1}` | 2 | `` |
| task_pages__form_section__sum_minus_amount_in_section_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__form_section__two_amount_arithmetic_value | `difference_two_amounts_in_section_value, sum_two_amounts_in_section_value` | `{'difference_two_amounts_in_section_value': 1, 'sum_two_amounts_in_section_value': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_condition_count | `field_value_above_threshold_count, field_value_below_threshold_count` | `{'field_value_above_threshold_count': 1, 'field_value_below_threshold_count': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_field_value_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_metric_extremum_label | `highest_field_value_callout_label, lowest_field_value_callout_label` | `{'highest_field_value_callout_label': 1, 'lowest_field_value_callout_label': 1}` | 2 | `` |
| task_pages__hierarchy__manager_most_direct_reports_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hierarchy__manager_most_total_reports_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hierarchy__subtree_descendant_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__global_metric_ranked_item_label | `nth_highest_metric_label, nth_lowest_metric_label` | `{'nth_highest_metric_label': 1, 'nth_lowest_metric_label': 1}` | 2 | `` |
| task_pages__infographic__metric_card_field_lookup | `detail_for_named_item, item_for_named_value, value_for_named_item` | `{'detail_for_named_item': 1, 'item_for_named_value': 1, 'value_for_named_item': 1}` | 3 | `` |
| task_pages__infographic__section_extrema_arithmetic_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_extremum_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_total_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_metric_ranked_item_label | `nth_highest_metric_in_section_label, nth_lowest_metric_in_section_label` | `{'nth_highest_metric_in_section_label': 1, 'nth_lowest_metric_in_section_label': 1}` | 2 | `` |
| task_pages__infographic__section_ranked_total_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_total_except_named_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_total_extrema_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__sum_named_metrics_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__instruction_panel__shared_control_for_step_set_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__instruction_panel__step_for_control_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__map__destination_after_directions_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__map__landmark_after_route_step_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_condition_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_ranked_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_value_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_two_field_condition_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__page_field_extremum_module_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__navigation_flow__navigation_path_target_label | `menu_path_target_label, ribbon_group_command_label, sidebar_tree_target_label` | `{'menu_path_target_label': 1, 'ribbon_group_command_label': 1, 'sidebar_tree_target_label': 1}` | 3 | `` |
| task_pages__navigation_flow__same_group_target_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__shortfall_minus_overage_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__sum_absolute_quantity_differences_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__total_amount_delta_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__process_flow__condition_path_endpoint_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__process_flow__filtered_node_count | `role_node_count, shape_node_count, status_node_count` | `{'role_node_count': 1, 'shape_node_count': 1, 'status_node_count': 1}` | 3 | `` |
| task_pages__process_flow__lane_filtered_handoff_count | `lane_involved_handoff_count, lane_outgoing_handoff_count` | `{'lane_involved_handoff_count': 1, 'lane_outgoing_handoff_count': 1}` | 2 | `` |
| task_pages__profile_card_grid__field_ranked_profile_label | `highest_field_profile_label, lowest_field_profile_label, nth_highest_field_profile_label, nth_lowest_field_profile_label` | `{'highest_field_profile_label': 1, 'lowest_field_profile_label': 1, 'nth_highest_field_profile_label': 1, 'nth_lowest_field_profile_label': 1}` | 4 | `` |
| task_pages__profile_card_grid__profile_for_field_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__profile_card_grid__value_for_named_profile_field | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__enabled_action_for_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__selected_rows_with_status_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__value_threshold_in_group_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__longer_than_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__maximum_non_overlapping_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__overlap_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__field_role_count | `all_field_count, attribute_field_count` | `{'all_field_count': 1, 'attribute_field_count': 1}` | 2 | `` |
| task_pages__schema__join_path_length_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_cardinality_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_endpoint_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__sectioned_infographic__section_filtered_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__sectioned_infographic__section_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__step_list__nth_step_field_label | `nth_step_detail, nth_step_title` | `{'nth_step_detail': 1, 'nth_step_title': 1}` | 2 | `` |
| task_pages__step_list__step_after_named_step_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__step_list__step_for_detail_label | `step_number_for_detail, step_title_for_detail` | `{'step_number_for_detail': 1, 'step_title_for_detail': 1}` | 2 | `` |
| task_pages__timeline__event_date_gap_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__timeline__interval_membership_count | `between_reference_events_count, outside_reference_interval_count` | `{'between_reference_events_count': 1, 'outside_reference_interval_count': 1}` | 2 | `` |
| task_pages__web_action__action_target_label | `click_target_label, select_option_label, type_field_label` | `{'click_target_label': 1, 'select_option_label': 1, 'type_field_label': 1}` | 3 | `` |
| task_pages__web_action__guide_code_target_count | `click_guide_code_target_count, select_option_guide_code_target_count, type_field_guide_code_target_count` | `{'click_guide_code_target_count': 1, 'select_option_guide_code_target_count': 1, 'type_field_guide_code_target_count': 1}` | 3 | `` |
| task_pages__workspace__context_control_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__workspace__control_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__workspace__dual_guide_control_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
