# Pages Task Setup

This document owns the active `pages` domain contract. Pages covers structured page-like artifacts, diagram-like page graphics, static maps, schedules, timelines, schemas, and GUI/web screens. Active tasks use the taxonomy-v0 `task_pages__<scene_id>__<objective_id>` id format.

## Active Scope
1. `domain=pages` covers visually structured artifacts whose answers are grounded in rendered local structure.
2. `task_group` remains the implementation/config grouping: `arithmetic`, `calendar`, `concept_map`, `cross_form`, `cycle`, `hierarchy`, `infographic`, `map`, `process_flow`, `schedule`, `schema`, `timeline`, `counting`, and `relation`.
3. Text stays OCR-light: short labels, field values, section headers, command labels, and visible guide cues.
4. Evidence must come from the same trace-backed visible units as the answer.
5. Active pages tasks expose one public sampling unit per `task_id` and put the concrete query branch in `query_id`. `query_id` is an internal replay selector, not a public sampling unit.

## Active Tasks
1. `task_pages__form_section__section_expression_value`
   - query_id: `sum_two_amounts_in_section|difference_two_amounts_in_section|sum_minus_amount_in_section`
   - scenes: `form_sheet|invoice_sheet|receipt_sheet`
   - answer/evidence: amount string, ordered operand-value `bbox_set`
2. `task_pages__paired_forms__reconciliation_value`
   - query_id: `total_amount_delta|shortfall_minus_overage_value|sum_absolute_quantity_differences`
   - scene: `purchase_receipt_pair`
   - answer/evidence: integer, matched item-code and numeric cell `bbox_set`
3. `task_pages__cycle__offset_stage_label`
   - query_id: `after_offset_stage_label|before_offset_stage_label`
   - internal axes: `query_relationship=after|before`, `cycle_direction=clockwise|counterclockwise`
   - scene: `cycle_ring`
   - answer/evidence: exact stage label, one target-stage bbox
4. `task_pages__hierarchy__tree_count`
   - query_id: `subtree_descendant_count|subtree_leaf_count|path_length_between_two_nodes`
   - scene: `rooted_tree`
   - answer/evidence: integer count, node-box `bbox_set`
5. `task_pages__map__navigation_label`
   - query_id: `destination_after_directions|landmark_after_route_step`
   - scene: `campus_map`
   - answer/evidence: exact landmark label, supporting route landmark `bbox_set`
6. `task_pages__calendar__weekday_occurrence_date`
   - query_id: `date_of_weekday_occurrence`
   - scene: `calendar`
   - answer/evidence: integer date, one date-cell `bbox_set`
7. `task_pages__calendar__marked_day_class_count`
   - query_id: `count_marked_weekend_days|count_marked_weekday_days`
   - scene: `calendar`
   - answer/evidence: integer count, marked date-cell `bbox_set`
8. `task_pages__concept_map__branch_item_count`
   - query_id: `branch_child_count`
   - scene: `concept_map`
   - visual contract: mixed rounded-rectangle, ellipse/pill, and circular concept-map nodes; node shape is visual variation, not a public task split
   - answer/evidence: integer count, counted child-item node `bbox_set`
9. `task_pages__concept_map__ordered_child_label`
   - query_id: `first_child_label|second_child_label|last_child_label`
   - scene: `concept_map`
   - answer/evidence: exact visible child-item label string, parent branch and answer child-item `bbox_set`
10. `task_pages__concept_map__filtered_node_count`
   - query_id: `marked_child_count`
   - scene: `concept_map`
   - answer/evidence: integer count, marked child-item node `bbox_set`
11. `task_pages__schedule__overlap_count`
   - query_id: `overlap_count`
   - scene: `schedule`
   - answer/evidence: integer count, event-block `bbox_set`
12. `task_pages__schedule__longer_than_reference_count`
   - query_id: `longer_than_reference_count`
   - scene: `schedule`
   - answer/evidence: integer count, reference/comparison event-block `bbox_set`
13. `task_pages__schedule__maximum_non_overlapping_count`
   - query_id: `maximum_non_overlapping_count`
   - scene: `schedule`
   - answer/evidence: integer optimum count, selected event-block `bbox_set`
14. `task_pages__timeline__interval_membership_count`
   - query_id: `between_reference_events_count|outside_reference_interval_count`
   - scene: `timeline`
   - answer/evidence: integer count, milestone event-card `bbox_set`
15. `task_pages__infographic__metric_arithmetic_value`
   - query_id: `sum_named_metrics|section_extrema_arithmetic|section_total_extrema_difference|section_total_except_named`
   - scene: `infographic`
   - answer/evidence: integer, metric label/value `bbox_set`
16. `task_pages__infographic__section_ranked_total_label`
   - query_id: `section_ranked_total_label`
   - scene: `infographic`
   - answer/evidence: section label string, answer-section label/value `bbox_set`
17. `task_pages__infographic__filtered_metric_total_value`
   - query_id: `section_icon_total_value`
   - scene: `infographic`
   - answer/evidence: integer, icon-filtered label/value `bbox_set`
18. `task_pages__infographic__column_profile_comparison_value`
   - query_id: `section_icon_total_difference_value`
   - scene: `infographic`
   - answer/evidence: integer, filtered label/value `bbox_set` from both sections
19. `task_pages__infographic__filtered_section_extremum_label`
   - query_id: `section_icon_extremum_label`
   - scene: `infographic`
   - answer/evidence: section label string, icon-filtered label/value `bbox_set` in the answer section
20. `task_pages__process_flow__filtered_node_count`
   - query_id: `shape_node_count|status_node_count|role_node_count`
   - scene: `process_flow`
   - answer/evidence: integer count, counted process-step `bbox_set`
21. `task_pages__process_flow__condition_path_endpoint_label`
   - query_id: `condition_path_endpoint_label`
   - scene: `process_flow`
   - answer/evidence: exact step label string, ordered step and decision-label `bbox_set`
22. `task_pages__process_flow__actor_handoff_count`
   - query_id: `all_cross_lane_handoff_count|lane_outgoing_handoff_count|lane_involved_handoff_count`
   - scene: `process_flow`
   - answer/evidence: integer count, counted handoff-arrow `bbox_set`
23. `task_pages__schema__field_role_count`
   - query_id: `all_field_count|attribute_field_count`
   - scene: `schema`
   - answer/evidence: integer count, counted schema-field row `bbox_set`
24. `task_pages__schema__relationship_count`
   - query_id: `total_relationship_count`
   - scene: `schema`
   - answer/evidence: integer count, counted relationship-line `bbox_set`
25. `task_pages__control_board__filter_count`
   - query_id: `disabled_controls_in_group_count|selected_enabled_controls_in_group_count|selected_rows_with_status_count|enabled_action_for_type_count|value_threshold_in_group_count`
   - scenes: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
   - answer/evidence: integer, full control-or-row `bbox_set`
26. `task_pages__navigation_flow__navigation_path_target_label`
   - query_id: `menu_path_target_label|sidebar_tree_target_label|ribbon_group_command_label`
   - answer/evidence: option letter, ordered navigation support/control `bbox_set`
27. `task_pages__command_matrix__command_intent_target_label`
   - query_id: `command_intent_target_label|dual_guide_command_label`
   - internal axis: `intent_category=create_insert|select_choose|view_toggle|edit_transform|format_style`
   - answer/evidence: option letter, ordered guide/object/header/control `bbox_set`
28. `task_pages__workspace__professional_target_label`
   - query_id: `toolbar_palette_control_label|property_panel_control_label|canvas_workspace_control_label|code_workspace_control_label|file_dialog_control_label`
   - answer/evidence: option letter, ordered guide/context/header/control `bbox_set`
29. `task_pages__web_action__web_action_target_label`
    - query_id: `click_target_label|type_field_label|select_option_label`
    - scenes: `shop_catalog|travel_booking|support_center|learning_portal|finance_portal|content_cms`
    - answer/evidence: option letter, ordered instruction/guide/context/control `bbox_set`

## Evidence Policy
1. Do not use full-page, full-window, decorative panel, or badge-only boxes as prompt-facing evidence.
2. Arithmetic evidence is ordered operand value boxes.
3. Cross-form evidence is the matched code/quantity/unit-value cells needed by the computation.
4. Cycle evidence is the target stage box only.
5. Hierarchy evidence is counted node sets or ordered path node boxes.
6. Map evidence is supporting route landmark boxes.
7. Calendar evidence stays on the relevant date cells, schedule evidence stays on event blocks, and timeline evidence stays on milestone event cards.
8. Infographic evidence uses metric label/value boxes that participate in the arithmetic or answer-section aggregate.
9. Concept-map evidence uses child-item node boxes and, for label queries, the parent branch box. These tasks intentionally use semantic branch membership and visible marker filters rather than graph-theory properties such as reachability, degree, or shortest paths.
10. Process-flow evidence uses counted step boxes, followed path boxes plus decision-label boxes, or counted handoff-arrow boxes. These tasks intentionally use lane/status/decision semantics rather than graph-theory properties such as shortest paths, reachability, or degree.
11. Database-schema evidence uses schema field rows, table boxes, and relationship lines. These tasks intentionally use schema semantics such as PK/FK roles and cardinality markers rather than graph-theory properties such as reachability or shortest paths.
12. GUI-like evidence uses full controls, rows, guide cards, context rows, headers, and instruction banners; candidate-label badge bboxes stay trace metadata only.

## Implementation Notes
1. Active task modules live under `trace/tasks/pages/<task_group>/`.
2. Shared page helpers live under `trace/tasks/pages/shared/`; helper names should describe the active page scene or visual scaffold they support.
3. Defaults live under `configs/domains/pages/`.
4. Prompt bundles live under `prompts/pages/<task_group>/` and use `pages_*_v0` bundle ids.

## Visual Variation
1. Page-like document/diagram tasks may sample paper/background tints, panel palettes, stroke widths, and deterministic layout jitter.
2. GUI-like tasks may sample light canvas tint, chrome/panel/control colors, and badge/control style colors.
3. Visual variation must not change target geometry, evidence alignment, font fit guarantees, or semantic answer uniqueness.
