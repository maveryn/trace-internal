# Pages Task Setup

This document owns the active `pages` domain contract. Pages covers structured page-like artifacts, diagram-like page graphics, static maps, schedules, timelines, schemas, and GUI/web screens. Active tasks use the taxonomy-v0 `task_pages__<scene_id>__<objective_id>` id format.

## Active Scope
1. `domain=pages` covers visually structured artifacts whose answers are grounded in rendered local structure.
2. `task_group` remains the implementation/config grouping: `arithmetic`, `calendar`, `concept_map`, `cross_form`, `cycle`, `document_lookup`, `hierarchy`, `infographic`, `map`, `process_flow`, `schedule`, `schema`, `step_list`, `timeline`, `counting`, and `relation`.
3. Text stays OCR-light: short labels, field values, section headers, command labels, and visible guide cues.
4. Evidence must come from the same trace-backed visible units as the answer.
5. Active pages tasks expose one public sampling unit per `task_id` and put the concrete query branch in `query_id`. `query_id` is an internal replay selector, not a public sampling unit.

## Active Tasks
1. `task_pages__form_section__section_expression_value`
   - query_id: `sum_two_amounts_in_section|difference_two_amounts_in_section|sum_minus_amount_in_section`
   - scene: `form_section`
   - visual scene variants: `form_sheet|invoice_sheet|receipt_sheet`
   - answer/evidence: amount string, role-keyed operand-value `keyed_bbox_map`
2. `task_pages__paired_forms__reconciliation_value`
   - query_id: `total_amount_delta|shortfall_minus_overage_value|sum_absolute_quantity_differences`
   - scene: `paired_forms`
   - visual scene variant: `purchase_receipt_pair`
   - answer/evidence: integer, full receiving-slip row `bbox_set` for rows whose received quantity differs from the matching purchase-order quantity
3. `task_pages__cycle__offset_stage_label`
   - query_id: `after_offset_stage_label|before_offset_stage_label`
   - internal axes: `query_relationship=after|before`, `cycle_direction=clockwise|counterclockwise`
   - scene: `cycle_ring`
   - answer/evidence: exact stage label, one target-stage bbox
4. `task_pages__hierarchy__subtree_node_count`
   - query_id: `subtree_descendant_count|subtree_leaf_count`
   - scene: `hierarchy`
   - visual scene variant: `rooted_tree`
   - answer/evidence: integer count, node-box `bbox_set`
5. `task_pages__hierarchy__path_length_count`
   - query_id: `path_length_between_two_nodes`
   - scene: `hierarchy`
   - visual scene variant: `rooted_tree`
   - answer/evidence: integer hop count, ordered path node-box `bbox_sequence`
6. `task_pages__map__navigation_label`
   - query_id: `destination_after_directions|landmark_after_route_step`
   - scene: `campus_map`
   - answer/evidence: exact landmark label, ordered supporting route landmark `bbox_sequence`
7. `task_pages__calendar__weekday_occurrence_date`
   - query_id: `date_of_weekday_occurrence`
   - scene: `calendar`
   - visual axes: `layout_mode=center_clean|free_jitter_clean|left_with_side_note|right_with_side_note|top_with_bottom_note`, `title_mode=none|generic|full_month_year`
   - answer/evidence: integer date, one date-cell `bbox_set`
8. `task_pages__calendar__marked_day_class_count`
   - query_id: `count_marked_weekend_days|count_marked_weekday_days`
   - scene: `calendar`
   - visual axes: same calendar layout/title modes as weekday occurrence; prompts do not reveal month name or year
   - answer/evidence: integer count, marked date-cell `bbox_set`
9. `task_pages__concept_map__node_filter_count`
   - query_id: `branch_child_count|marked_child_count`
   - scene: `concept_map`
   - visual contract: mixed rounded-rectangle, ellipse/pill, and circular concept-map nodes; node shape is visual variation, not a public task split
   - answer/evidence: integer count, counted child-item-node `bbox_set`
10. `task_pages__concept_map__ordered_child_label`
   - query_id: `nth_child_label`
   - scene: `concept_map`
   - answer/evidence: exact visible child-item label string, parent branch and answer child-item `keyed_bbox_map`
11. `task_pages__schedule__reference_interval_count`
   - query_id: `overlap_count|longer_than_reference_count`
   - scene: `schedule`
   - answer/evidence: integer count, reference/comparison event-block `bbox_set`
12. `task_pages__schedule__maximum_non_overlapping_count`
   - query_id: `maximum_non_overlapping_count`
   - scene: `schedule`
   - answer/evidence: integer optimum count, selected event-block `bbox_set`
13. `task_pages__timeline__interval_membership_count`
   - query_id: `between_reference_events_count|outside_reference_interval_count`
   - scene: `timeline`
   - answer/evidence: integer count, milestone event-card `bbox_set`
14. `task_pages__step_list__ordinal_step_detail_label`
   - query_id: `nth_step_title|nth_step_detail|step_after_named_step`
   - scene: `step_list`
   - answer/evidence: exact visible title/detail string, role-keyed target/source title-detail `keyed_bbox_map`
15. `task_pages__profile_card_grid__attribute_lookup_label`
   - query_id: `value_for_named_profile_field|profile_for_field_value`
   - scene: `profile_card_grid`
   - answer/evidence: exact visible profile name or field value string, profile-name, field-label, and field-value `keyed_bbox_map`
16. `task_pages__ranked_list__ordinal_entry_label`
   - query_id: `nth_entry_label|from_end_entry_label|entry_after_named_entry`
   - scene: `ranked_list`
   - answer/evidence: exact visible ranked-list item string, role-keyed section-title, target-item, and optional source-item `keyed_bbox_map`
17. `task_pages__infographic__metric_arithmetic_value`
   - query_id: `sum_named_metrics|section_extrema_arithmetic|section_total_extrema_difference|section_total_except_named|section_icon_total_value|section_icon_total_difference_value`
   - scene: `infographic`
   - answer/evidence: integer, supporting metric-card `keyed_bbox_map`
18. `task_pages__infographic__section_rank_label`
   - query_id: `section_ranked_total_label|section_icon_extremum_label`
   - scene: `infographic`
   - answer/evidence: section label string, answer-section metric-card `keyed_bbox_map`
19. `task_pages__infographic__fact_lookup_label`
   - query_id: `value_for_named_item|item_for_named_value|detail_for_named_item`
   - scene: `infographic`
   - answer/evidence: exact visible string, supporting metric-card `keyed_bbox_map`
20. `task_pages__process_flow__filtered_node_count`
   - query_id: `shape_node_count|status_node_count|role_node_count`
   - scene: `process_flow`
   - answer/evidence: integer count, counted process-step `bbox_set`
21. `task_pages__process_flow__condition_path_endpoint_label`
   - query_id: `condition_path_endpoint_label`
   - scene: `process_flow`
   - answer/evidence: exact step label string, compact role-keyed path witness `keyed_bbox_map` with `start_step`, decision-label, intermediate-step, and endpoint-step roles
22. `task_pages__process_flow__actor_handoff_count`
   - query_id: `all_cross_lane_handoff_count|lane_outgoing_handoff_count|lane_involved_handoff_count`
   - scene: `process_flow`
   - answer/evidence: integer count, counted handoff-arrow `point_pair_set`
23. `task_pages__schema__field_role_count`
   - query_id: `all_field_count|attribute_field_count`
   - scene: `schema`
   - answer/evidence: integer count, counted schema-field row `bbox_set`
24. `task_pages__schema__relationship_count`
   - query_id: `total_relationship_count`
   - scene: `schema`
   - answer/evidence: integer count, counted relationship-line endpoint `point_pair_set`
25. `task_pages__control_board__control_filter_count`
   - query_id: `disabled_controls_in_group_count|selected_enabled_controls_in_group_count`
   - scene: `control_board`
   - visual scene variants: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
   - answer/evidence: integer, full control `bbox_set`
26. `task_pages__data_table__row_filter_count`
   - query_id: `selected_rows_with_status_count|enabled_action_for_type_count|value_threshold_in_group_count`
   - scene: `data_table`
   - visual scene variants: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
   - answer/evidence: integer, full table-row `bbox_set`
27. `task_pages__navigation_flow__navigation_path_target_label`
   - query_id: `menu_path_target_label|sidebar_tree_target_label|ribbon_group_command_label`
   - answer/evidence: option letter, query-specific role-keyed navigation support/control `keyed_bbox_map`
28. `task_pages__command_matrix__command_intent_target_label`
   - query_id: `command_intent_target_label|dual_guide_command_label`
   - internal axis: `intent_category=create_insert|select_choose|view_toggle|edit_transform|format_style`
   - answer/evidence: option letter, role-keyed action-cue guide, optional object-cue guide, object row, action-code header, and target command-cell `keyed_bbox_map`
29. `task_pages__workspace__professional_target_label`
   - query_id: `toolbar_palette_control_label|property_panel_control_label|canvas_workspace_control_label|code_workspace_control_label|file_dialog_control_label`
   - answer/evidence: option letter, query-specific role-keyed cue card, context row, code header, and target control `keyed_bbox_map` using keys such as `tool_cue_card`, `code_target_row`, `ide_code_header`, or `target_file_dialog_control`
30. `task_pages__web_action__web_action_target_label`
    - query_id: `click_target_label|type_field_label|select_option_label`
    - scenes: `shop_catalog|travel_booking|support_center|learning_portal|finance_portal|content_cms`
    - answer/evidence: option letter, query-specific role-keyed instruction, cue-guide, context unit, and target web-control `keyed_bbox_map`

## Evidence Policy
1. Do not use full-page, full-window, decorative panel, or badge-only boxes as prompt-facing evidence.
2. Arithmetic evidence is a `keyed_bbox_map` over the operand value boxes named in the prompt expression, using role keys such as `first_operand`, `second_operand`, and `third_operand` so expression order is verifiable.
3. Cross-form reconciliation evidence uses a `bbox_set` over full mismatched receiving-slip rows. The verifier treats row order as irrelevant; private trace metadata retains the matched purchase/receiving cell ids needed for audit.
4. Cycle evidence is the target stage box only.
5. Hierarchy evidence is counted subtree node `bbox_set` evidence or ordered path-node `bbox_sequence` evidence.
6. Map evidence is ordered supporting route landmark `bbox_sequence` evidence.
7. Calendar evidence stays on the relevant date cells, schedule evidence stays on event blocks, timeline evidence stays on milestone event cards, and step-list/ranked-list evidence stays on role-keyed section/source text plus target answer text needed to identify the answer.
8. Profile-card evidence uses `keyed_bbox_map` evidence for the profile name, field label, and field value that jointly identify the answer.
9. Infographic evidence uses `keyed_bbox_map` metric-card boxes keyed by visible metric-card labels. Arithmetic queries include the supporting cards used by the computation; answer-section aggregate and direct lookup queries include the supporting answer card set.
10. Concept-map count evidence uses child-item node boxes; label-query evidence uses a role-keyed parent branch and answer child-item map. These tasks intentionally use semantic branch membership and visible marker filters rather than graph-theory properties such as reachability, degree, or shortest paths.
11. Process-flow evidence uses counted step boxes, compact role-keyed path witnesses, or counted handoff-arrow endpoint pairs. These tasks intentionally use lane/status/decision semantics rather than graph-theory properties such as shortest paths, reachability, or degree.
12. Database-schema evidence uses schema field rows, table boxes, and relationship-line endpoint pairs. These tasks intentionally use schema semantics such as PK/FK roles and cardinality markers rather than graph-theory properties such as reachability or shortest paths.
13. GUI-like evidence uses full controls, rows, guide cards, context rows, headers, and instruction banners; candidate-label badge bboxes stay trace metadata only. Role-bound GUI tasks should use `keyed_bbox_map` with concrete visual role names such as `action_cue_guide`, `target_command_cell`, `code_target_row`, `ide_code_header`, `item_card`, or `target_button`, not generic placeholders like `path_context` or `target_control`.

## Implementation Notes
1. Active task modules live under `trace/tasks/pages/<task_group>/`.
2. Shared page helpers live under `trace/tasks/pages/shared/`; helper names should describe the active page scene or visual scaffold they support.
3. Defaults live under `configs/domains/pages/`.
4. Prompt bundles live under `prompts/pages/<task_group>/` and use `pages_*_v0` bundle ids.
5. Pages tasks are wrapped at registration by the pages render-audit defaults in `trace/tasks/pages/shared/render_audit_defaults.py`.
   - The wrapper samples one `pages_default_font_family` from the readout font pool for each instance and sets it as the implicit font family for all page text that does not pass an explicit family.
   - The wrapper records `render_spec.font_assets.asset_version`, `render_spec.font_assets.pages_default_font_family`, and the sampling policy.
   - The wrapper may draw non-answer context text from `assets/context_text/` into safe post-render margins. It records the layer under `render_spec.context_text_layer` and `render_map.context_text_bboxes_px`; context text is excluded from semantic `scene_ir.entities[]` and answer/evidence contracts.
   - The default context-density weights are moderately distractor-rich: `light` and `one_side_note` are common, `two_side_notes` is occasional when margins are safe, and `clean` remains a small share. Scene/task configs may tune this through `visual.context_text`, and explicit params such as `pages_context_density` or `pages_context_density_weights` remain available for targeted reviews or calibration.
   - Set `pages_context_text_enabled=false` or `context_text_enabled=false` to disable the safe-margin context layer for targeted reviews/calibration.
6. Structured-document scenes may sample `document_layout_mode` before applying deterministic jitter.
   - Supported modes keep documents inside safe bounds while varying the page placement, for example centered, left/right weighted, and upper/lower corner-weighted placements.
   - Evidence bboxes and context-text safety checks must be computed after the final page placement and jitter, never from a pre-placement template.

## Visual Variation
1. Page-like document/diagram tasks may sample paper/background tints, panel palettes, stroke widths, and deterministic layout jitter.
2. GUI-like tasks may sample light canvas tint, chrome/panel/control colors, and badge/control style colors.
3. Visual variation must not change target geometry, evidence alignment, font fit guarantees, or semantic answer uniqueness.
4. Page text should sample from the readout font pool by default. Excluding font subsets for a page scene requires a documented readability reason.
5. Non-answer page context text must come from the shared context-text assets, stay independent of answers/query branches, avoid overlap with traced evidence/entities, and remain out of prompt/evidence contracts unless a task explicitly promotes it into the verifier contract. Longer side-note blocks are allowed only as controlled density variants; they should add page variety without becoming the main semantic artifact.
6. Calendar scenes may reserve side or bottom whitespace for non-answer paragraph notes. The calendar panel position is sampled from fractions of the remaining free canvas space after panel sizing, so jitter scales with available layout room rather than a fixed pixel offset. Month/year may appear only as a visual title variant, never as prompt text.
