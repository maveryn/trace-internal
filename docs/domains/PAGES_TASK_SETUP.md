# Pages Task Setup

This document owns the active `pages` domain contract. Pages covers structured page-like artifacts, diagram-like page graphics, static maps, schedules, timelines, schemas, and GUI/web screens. Active tasks use the taxonomy-v0 `task_pages__<scene_id>__<objective_id>` id format.

## Active Scope
1. `domain=pages` covers visually structured artifacts whose answers are grounded in rendered local structure.
2. `task_group` remains the implementation/config grouping: `arithmetic`, `calendar`, `concept_map`, `cross_form`, `cycle`, `document_lookup`, `hierarchy`, `infographic`, `map`, `process_flow`, `schedule`, `schema`, `step_list`, `timeline`, `counting`, and `relation`.
3. Text stays OCR-light: short labels, field values, section headers, command labels, and visible guide cues.
4. Annotation must come from the same trace-backed visible units as the answer.
5. Active pages tasks expose one public sampling unit per `task_id` and put the concrete query branch in `query_id`. `query_id` is an internal replay selector, not a public sampling unit.

## Active Tasks
Pages currently has 92 active public task ids. Public task ids are the sampling units; `query_id` remains an internal replay/operand selector.

| Scene | Task id | Query contract | Answer / annotation |
| --- | --- | --- | --- |
| `calendar` | `task_pages__calendar__marked_day_class_count` | `count_marked_weekday_days`, `count_marked_weekend_days` | integer count / marked date-cell `bbox_set` |
| `calendar` | `task_pages__calendar__workday_offset_date` | `workday_after_offset_date`, `workday_before_offset_date` | integer date / reference and target date-cell `keyed_bbox_map` |
| `calendar` | `task_pages__calendar__weekday_occurrence_date` | `date_of_weekday_occurrence` | integer date / target date-cell `bbox_set` |
| `calendar_event_grid` | `task_pages__calendar_event_grid__category_slot_day_count` | `category_slot_day_count` | integer count / matching event-chip `bbox_set` |
| `calendar_event_grid` | `task_pages__calendar_event_grid__date_for_category_slot_label` | `date_for_category_slot_label` | integer date / date cell and event chip `keyed_bbox_map` |
| `calendar_event_grid` | `task_pages__calendar_event_grid__date_slot_category_label` | `date_slot_category_label` | category label / date cell and event chip `keyed_bbox_map` |
| `category_grid` | `task_pages__category_grid__category_item_count` | `category_item_count` | integer count / item-row `bbox_set` under one category/subcategory block |
| `category_grid` | `task_pages__category_grid__category_slot_item_label` | `category_slot_item_label` | item label / category header, subcategory header, target item `keyed_bbox_map` |
| `command_matrix` | `task_pages__command_matrix__command_intent_target_label` | `command_intent_target_label` | option letter / role-keyed guide, row, header, target `keyed_bbox_map` |
| `command_matrix` | `task_pages__command_matrix__dual_guide_command_label` | `dual_guide_command_label` | option letter / role-keyed guides, row, header, target `keyed_bbox_map` |
| `comparison_panel` | `task_pages__comparison_panel__side_attribute_value_label` | `side_attribute_value_label` | visible value / side header, attribute label, value cell `keyed_bbox_map` |
| `concept_map` | `task_pages__concept_map__branch_child_count` | `branch_child_count` | integer count / child-item-node `bbox_set` |
| `concept_map` | `task_pages__concept_map__marked_child_count` | `marked_child_count` | integer count / marked child-item-node `bbox_set` |
| `concept_map` | `task_pages__concept_map__ordered_child_label` | `nth_child_label` | child label / parent branch and answer child `keyed_bbox_map` |
| `control_board` | `task_pages__control_board__disabled_controls_in_group_count` | `disabled_controls_in_group_count` | integer count / full control `bbox_set` |
| `control_board` | `task_pages__control_board__selected_enabled_controls_in_group_count` | `selected_enabled_controls_in_group_count` | integer count / full control `bbox_set` |
| `cycle` | `task_pages__cycle__offset_stage_label` | `after_offset_stage_label`, `before_offset_stage_label` | stage label / target-stage bbox |
| `form_section` | `task_pages__form_section__difference_two_amounts_in_section_value` | `difference_two_amounts_in_section` | currency string / operand-value `keyed_bbox_map` |
| `form_section` | `task_pages__form_section__sum_minus_amount_in_section_value` | `sum_minus_amount_in_section` | currency string / operand-value `keyed_bbox_map` |
| `form_section` | `task_pages__form_section__sum_two_amounts_in_section_value` | `sum_two_amounts_in_section` | currency string / operand-value `keyed_bbox_map` |
| `hierarchy` | `task_pages__hierarchy__path_length_count` | `path_length_between_two_nodes` | integer path length / ordered path-node `bbox_sequence` |
| `hierarchy` | `task_pages__hierarchy__subtree_descendant_count` | `subtree_descendant_count` | integer count / descendant node `bbox_set` |
| `hierarchy` | `task_pages__hierarchy__subtree_leaf_count` | `subtree_leaf_count` | integer count / leaf node `bbox_set` |
| `infographic` | `task_pages__infographic__detail_for_named_item` | `detail_for_named_item` | visible detail string / metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__item_for_named_value` | `item_for_named_value` | visible item label / metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__metric_ranked_item_label` | `nth_highest_metric_label`, `nth_lowest_metric_label`, `nth_highest_metric_in_section_label`, `nth_lowest_metric_in_section_label` | metric-card label / target metric label, target value, and optional section title `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_extrema_arithmetic_value` | `section_extrema_arithmetic` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_icon_extremum_label` | `section_icon_extremum_label` | section label / answer-section metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_icon_total_difference_value` | `section_icon_total_difference_value` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_icon_total_value` | `section_icon_total_value` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_ranked_total_label` | `section_ranked_total_label` | section label / answer-section metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_total_except_named_value` | `section_total_except_named` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__section_total_extrema_difference_value` | `section_total_extrema_difference` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__sum_named_metrics_value` | `sum_named_metrics` | integer / supporting metric-card `keyed_bbox_map` |
| `infographic` | `task_pages__infographic__value_for_named_item` | `value_for_named_item` | visible value string / metric-card `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_field_value_label` | `module_field_value_label` | visible value from irregular mixed modules / module title, item label, field label, value cell `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_field_extremum_item_label` | `module_field_extremum_item_label` | item label / module title, field label, winning item/value, and compared value `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_field_ranked_item_label` | `module_field_ranked_item_label` | item label / module title, field label, ranked item/value, and compared value `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__page_field_extremum_module_label` | `page_field_extremum_module_label` | module title / winning module title, field label, winning item/value, and page-wide compared value `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_two_field_condition_item_label` | `module_two_field_condition_item_label` | item label / module title, numeric field label, categorical field label, matching item, and supporting value cells `keyed_bbox_map` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_condition_item_count` | `module_condition_item_count` | integer count / matching value-cell `bbox_set` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__module_field_total_value` | `module_field_total_value` | integer total / summed value-cell `bbox_set` |
| `mixed_infographic_page` | `task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label` | `two_module_field_total_comparison_module_label` | module title / two module titles, field labels, and summed value cells `keyed_bbox_map` |
| `hero_callout_infographic` | `task_pages__hero_callout_infographic__callout_field_value_label` | `callout_field_value_label` | visible value / callout title, field label, value cell `keyed_bbox_map` |
| `hero_callout_infographic` | `task_pages__hero_callout_infographic__callout_metric_extremum_label` | `callout_metric_extremum_label` | callout title / winning title, field label, winning value, and compared values `keyed_bbox_map` |
| `hero_callout_infographic` | `task_pages__hero_callout_infographic__callout_condition_count` | `callout_condition_count` | integer count / matching value-cell `bbox_set` |
| `sectioned_infographic` | `task_pages__sectioned_infographic__section_filtered_item_label` | `section_filtered_item_label` | item label / section title, filter marker, target item `keyed_bbox_map` |
| `sectioned_infographic` | `task_pages__sectioned_infographic__section_item_count` | `section_item_count` | integer count / visible item-row `bbox_set` |
| `map` | `task_pages__map__destination_after_directions_label` | `destination_after_directions` | landmark label / ordered route landmark `bbox_sequence` |
| `map` | `task_pages__map__landmark_after_route_step_label` | `landmark_after_route_step` | landmark label / ordered route landmark `bbox_sequence` |
| `navigation_flow` | `task_pages__navigation_flow__menu_path_target_label` | `menu_path_target_label` | option letter / navigation support-control `keyed_bbox_map` |
| `navigation_flow` | `task_pages__navigation_flow__ribbon_group_command_label` | `ribbon_group_command_label` | option letter / navigation support-control `keyed_bbox_map` |
| `navigation_flow` | `task_pages__navigation_flow__sidebar_tree_target_label` | `sidebar_tree_target_label` | option letter / navigation support-control `keyed_bbox_map` |
| `paired_forms` | `task_pages__paired_forms__shortfall_minus_overage_value` | `shortfall_minus_overage_value` | integer / mismatched receiving-slip row `bbox_set` |
| `paired_forms` | `task_pages__paired_forms__sum_absolute_quantity_differences_value` | `sum_absolute_quantity_differences` | integer / mismatched receiving-slip row `bbox_set` |
| `paired_forms` | `task_pages__paired_forms__total_amount_delta_value` | `total_amount_delta` | integer / mismatched receiving-slip row `bbox_set` |
| `process_flow` | `task_pages__process_flow__all_cross_lane_handoff_count` | `all_cross_lane_handoff_count` | integer count / handoff-arrow `point_pair_set` |
| `process_flow` | `task_pages__process_flow__condition_path_endpoint_label` | `condition_path_endpoint_label` | step label / path witness `keyed_bbox_map` |
| `process_flow` | `task_pages__process_flow__filtered_node_count` | `shape_node_count`, `status_node_count`, `role_node_count` | integer count / process-step `bbox_set` |
| `process_flow` | `task_pages__process_flow__lane_filtered_handoff_count` | `lane_outgoing_handoff_count`, `lane_involved_handoff_count` | integer count / handoff-arrow `point_pair_set` |
| `profile_card_grid` | `task_pages__profile_card_grid__profile_for_field_value` | `profile_for_field_value` | profile name / profile-name, field-label, field-value `keyed_bbox_map` |
| `profile_card_grid` | `task_pages__profile_card_grid__field_extremum_profile_label` | `highest_field_profile_label`, `lowest_field_profile_label` | profile name / target profile, field label, target value `keyed_bbox_map` |
| `profile_card_grid` | `task_pages__profile_card_grid__field_ranked_profile_label` | `nth_highest_field_profile_label`, `nth_lowest_field_profile_label` | profile name / target profile, field label, target value `keyed_bbox_map` |
| `profile_card_grid` | `task_pages__profile_card_grid__value_for_named_profile_field` | `value_for_named_profile_field` | field value / profile-name, field-label, field-value `keyed_bbox_map` |
| `ranked_list` | `task_pages__ranked_list__entry_after_named_entry_label` | `entry_after_named_entry` | ranked-list item / section, source item, target item `keyed_bbox_map` |
| `ranked_list` | `task_pages__ranked_list__ordinal_entry_label` | `nth_entry_label`, `from_end_entry_label` | ranked-list item / section and target item `keyed_bbox_map` |
| `record_table` | `task_pages__record_table__enabled_action_for_type_count` | `enabled_action_for_type_count` | integer count / full record-row `bbox_set` |
| `record_table` | `task_pages__record_table__selected_rows_with_status_count` | `selected_rows_with_status_count` | integer count / full record-row `bbox_set` |
| `record_table` | `task_pages__record_table__value_threshold_in_group_count` | `value_threshold_in_group_count` | integer count / full record-row `bbox_set` |
| `schedule` | `task_pages__schedule__longer_than_reference_count` | `longer_than_reference_count` | integer count / comparison event-block `bbox_set` |
| `schedule` | `task_pages__schedule__maximum_non_overlapping_count` | `maximum_non_overlapping_count` | integer optimum / selected event-block `bbox_set` |
| `schedule` | `task_pages__schedule__overlap_count` | `overlap_count` | integer count / overlapping event-block `bbox_set` |
| `schema` | `task_pages__schema__field_role_count` | `all_field_count`, `attribute_field_count` | integer count / schema-field row `bbox_set` |
| `schema` | `task_pages__schema__relationship_cardinality_label` | `relationship_cardinality_between_tables` | cardinality label / endpoint tables and cardinality markers `keyed_bbox_map` |
| `schema` | `task_pages__schema__relationship_endpoint_label` | `target_table_for_relationship_label` | table label / source table, relationship label, and target table `keyed_bbox_map` |
| `schema` | `task_pages__schema__relationship_count` | `total_relationship_count` | integer count / relationship-line endpoint `point_pair_set` |
| `instruction_panel` | `task_pages__instruction_panel__shared_control_for_step_set_label` | `shared_control_for_step_set_label` | control label / referenced step-number badges and shared control chips `keyed_bbox_set_map` |
| `instruction_panel` | `task_pages__instruction_panel__step_for_control_pair_label` | `step_for_control_pair_label` | integer step number / two matching control chips and step-number badge `keyed_bbox_map` |
| `step_list` | `task_pages__step_list__nth_step_detail_label` | `nth_step_detail` | step detail / target detail `keyed_bbox_map` |
| `step_list` | `task_pages__step_list__nth_step_title_label` | `nth_step_title` | step title / target title `keyed_bbox_map` |
| `step_list` | `task_pages__step_list__step_after_named_step_label` | `step_after_named_step` | next-step title / source and target title `keyed_bbox_map` |
| `step_list` | `task_pages__step_list__step_for_detail_label` | `step_title_for_detail`, `step_number_for_detail` | step title or number / source detail and target title or number `keyed_bbox_map` |
| `timeline` | `task_pages__timeline__event_date_gap_value` | `event_date_gap_value` | integer day gap / endpoint event-card `keyed_bbox_map` |
| `timeline` | `task_pages__timeline__interval_membership_count` | `between_reference_events_count`, `outside_reference_interval_count` | integer count / milestone event-card `bbox_set` |
| `web_action` | `task_pages__web_action__click_target_label` | `click_target_label` | option letter / instruction, guide, item card, target button `keyed_bbox_map` |
| `web_action` | `task_pages__web_action__select_option_label` | `select_option_label` | option letter / instruction, guide, option group, target option `keyed_bbox_map` |
| `web_action` | `task_pages__web_action__type_field_label` | `type_field_label` | option letter / instruction, guide, form section, target input `keyed_bbox_map` |
| `workspace` | `task_pages__workspace__canvas_workspace_control_label` | `canvas_workspace_control_label` | option letter / cue card, context row, code header, target control `keyed_bbox_map` |
| `workspace` | `task_pages__workspace__code_workspace_control_label` | `code_workspace_control_label` | option letter / cue card, context row, code header, target control `keyed_bbox_map` |
| `workspace` | `task_pages__workspace__file_dialog_control_label` | `file_dialog_control_label` | option letter / cue card, context row, code header, target control `keyed_bbox_map` |
| `workspace` | `task_pages__workspace__property_panel_control_label` | `property_panel_control_label` | option letter / cue card, context row, code header, target control `keyed_bbox_map` |
| `workspace` | `task_pages__workspace__toolbar_palette_control_label` | `toolbar_palette_control_label` | option letter / cue card, context row, code header, target control `keyed_bbox_map` |

## Annotation Policy
1. Do not use full-page, full-window, decorative panel, or badge-only boxes as prompt-facing annotation.
2. Arithmetic annotation is a `keyed_bbox_map` over the operand value boxes named in the prompt expression, using role keys such as `first_operand`, `second_operand`, and `third_operand` so expression order is verifiable.
3. Cross-form reconciliation annotation uses a `bbox_set` over full mismatched receiving-slip rows. The verifier treats row order as irrelevant; private trace metadata retains the matched purchase/receiving cell ids needed for audit.
4. Cycle annotation is the target stage box only.
5. Hierarchy annotation is counted subtree node `bbox_set` annotation or ordered path-node `bbox_sequence` annotation.
6. Map annotation is ordered supporting route landmark `bbox_sequence` annotation.
7. Calendar annotation stays on the relevant date cells or event chips, schedule annotation stays on event blocks, timeline annotation stays on milestone event cards, and step-list/ranked-list annotation stays on role-keyed section/source text plus target answer text needed to identify the answer. Instruction-panel annotation stays on the referenced step-number badges and visible control chips; use keyed annotation when step and control roles differ. Event-grid calendar lookup uses keyed date-cell and event-chip annotation because the roles differ. Timeline date-gap annotation uses endpoint-card keys when the two endpoint roles matter.
8. Profile-card annotation uses `keyed_bbox_map` annotation for the profile name, field label, and field value that jointly identify the answer. Comparison-panel lookup annotation uses `side_header`, `attribute_label`, and `value_cell` keys because the row and column witnesses play different roles.
9. Infographic annotation uses `keyed_bbox_map` metric-card boxes keyed by visible metric-card labels. Arithmetic queries include the supporting cards used by the computation; answer-section aggregate and direct lookup queries include the supporting answer card set. Mixed-infographic direct lookup uses role-keyed `module_title`, `item_label`, `field_label`, and `value_cell` boxes because the lookup depends on binding page-module roles. Mixed-infographic extremum uses keyed module/field/winner/compared-value boxes; mixed-infographic count and total tasks use `bbox_set` annotation over the matching or summed value cells. Hero-callout lookup and extremum tasks use role-keyed callout title, field label, and value-cell annotation because the visual roles differ; hero-callout condition count uses a `bbox_set` over matching value cells. Sectioned-infographic item counts use a `bbox_set` over the visible item rows in the requested section, with section title boxes retained in trace metadata for audit.
10. Concept-map count annotation uses child-item node boxes; label-query annotation uses a role-keyed parent branch and answer child-item map. These tasks intentionally use semantic branch membership and visible marker filters rather than graph-theory properties such as reachability, degree, or shortest paths.
11. Process-flow annotation uses counted step boxes, compact role-keyed path witnesses, or counted handoff-arrow endpoint pairs. These tasks intentionally use lane/status/decision semantics rather than graph-theory properties such as shortest paths, reachability, or degree.
12. Database-schema annotation uses schema field rows, table boxes, relationship-label boxes, and relationship-line endpoint pairs. Role-bound endpoint lookups use `keyed_bbox_map` keys such as `source_table`, `relationship_label`, and `target_table`. These tasks intentionally use schema semantics such as PK/FK roles and cardinality markers rather than graph-theory properties such as reachability or shortest paths.
13. GUI-like annotation uses full controls, rows, guide cards, context rows, headers, and instruction banners; candidate-label badge bboxes stay trace metadata only. Role-bound GUI tasks should use `keyed_bbox_map` with concrete visual role names such as `action_cue_guide`, `target_command_cell`, `code_target_row`, `ide_code_header`, `item_card`, or `target_button`, not generic placeholders like `path_context` or `target_control`.

## Table Boundary
1. `pages/record_table` is for UI/document record lists where rows carry workflow-like state such as selected, status, type, action availability, section/group, or file-size metadata.
2. `charts/table` owns analytic data-table reasoning where the table itself is the data display, including row/column conditions, ranks, numeric differences, percent growth, summaries, and chart-table arithmetic.
3. Do not add generic analytic table lookup or arithmetic tasks to `pages/record_table`; use the charts domain unless the prompt is grounded in document/UI record semantics.

## Implementation Notes
1. Active task modules live under `trace/tasks/pages/<task_group>/`.
2. Shared page helpers live under `trace/tasks/pages/shared/`; helper names should describe the active page scene or visual scaffold they support.
3. Defaults live under `configs/domains/pages/`.
4. Prompt bundles live under `prompts/pages/<task_group>/` and use `pages_*_v0` bundle ids.
5. Pages tasks are wrapped at registration by the pages render-audit defaults in `trace/tasks/pages/shared/render_audit_defaults.py`.
   - The wrapper samples one `pages_default_font_family` from the readout font pool for each instance and sets it as the implicit font family for all page text that does not pass an explicit family.
   - The wrapper records `render_spec.font_assets.asset_version`, `render_spec.font_assets.pages_default_font_family`, and the sampling policy.
   - The wrapper may draw non-answer context text from `assets/context_text/` into safe post-render margins. It records the layer under `render_spec.context_text_layer` and `render_map.context_text_bboxes_px`; context text is excluded from semantic `scene_ir.entities[]` and answer/annotation contracts.
   - The default context-density weights are moderately distractor-rich: `light` and `one_side_note` are common, `two_side_notes` is occasional when margins are safe, and `clean` remains a small share. Scene/task configs may tune this through `visual.context_text`, and explicit params such as `pages_context_density` or `pages_context_density_weights` remain available for targeted reviews or calibration.
   - Set `pages_context_text_enabled=false` or `context_text_enabled=false` to disable the safe-margin context layer for targeted reviews/calibration.
   - Page scenes that need reusable visible labels should use `trace/tasks/pages/shared/page_text_resources.py`, which wraps shared label and context-text manifests with page-local length/uniqueness filters and records selected resource metadata under `render_spec.page_text_resources`.
   - `mixed_infographic_page` disables the post-render safe-margin context layer by default because contextual notes are native infographic content in that scene. Its renderer always includes large wrapped paragraph-style panels plus smaller notes, samples `native_layout_mode` to place those blocks in footer/header/side-rail/poster/corner arrangements, records those blocks under `render_spec.infographic_text_blocks` and `render_map.infographic_text_block_bboxes_px`, and keeps task annotation on the requested module/item/field/value witnesses rather than native context text. It uses the pages-owned asset pool under `assets/pages/visual_assets/` for non-answer `hero_anchor`, module `section_illustration`, and item `badge_spot` visuals; selected assets are recorded under `render_spec.page_visual_assets` and corresponding bboxes under `render_map.visual_asset_bboxes_px`. Compact radial, ring, profile-card, and callout modules cap item/field density where needed so label/value text bands remain separated.
   - `hero_callout_infographic` disables the post-render safe-margin context layer by default and uses pages-owned visual assets as non-answer page content: one large `hero_anchor`, one decorative `section_illustration`, and per-callout `badge_spot` assets. Its layout variants place titled callout cards around, beside, or below the hero asset while keeping annotation on visible callout title, field-label, and value-cell witnesses.
   - Pages visual assets are decorative by default. Tasks may use answer-bearing icons or markers only through the curated semantic overlay in `trace/tasks/pages/shared/page_semantic_assets.py`, backed by `assets/pages/visual_assets/semantic_overlay.jsonl`. Render specs must record the semantic id, display label, resolved asset id, and overlay metadata under `render_spec.page_semantic_assets`.
6. Structured-document scenes may sample `document_layout_mode` before applying deterministic jitter.
   - Supported modes keep documents inside safe bounds while varying the page placement, for example centered, left/right weighted, and upper/lower corner-weighted placements.
   - Annotation bboxes and context-text safety checks must be computed after the final page placement and jitter, never from a pre-placement template.

## Visual Variation
1. Page-like document/diagram tasks may sample paper/background tints, panel palettes, stroke widths, and deterministic layout jitter.
2. GUI-like tasks may sample light canvas tint, chrome/panel/control colors, and badge/control style colors.
3. Visual variation must not change target geometry, annotation alignment, font fit guarantees, or semantic answer uniqueness.
4. Page text should sample from the readout font pool by default. Excluding font subsets for a page scene requires a documented readability reason.
5. Non-answer page context text must come from the shared context-text assets, stay independent of answers/query branches, avoid overlap with traced annotation/entities, and remain out of prompt/annotation contracts unless a task explicitly promotes it into the verifier contract. Longer side-note blocks are allowed only as controlled density variants; they should add page variety without becoming the main semantic artifact.
6. Calendar scenes may reserve side or bottom whitespace for non-answer paragraph notes. The calendar panel position is sampled from fractions of the remaining free canvas space after panel sizing, so jitter scales with available layout room rather than a fixed pixel offset. Month/year may appear only as a visual title variant, never as prompt text. Calendar `surface_mode` should be balanced roughly evenly across light and dark themes, and `text_color_mode` should vary label ink color while keeping title, weekday, date, marker, and event-chip text contrast-safe.
7. `calendar_event_grid` uses short visible text chips in fixed event slots. Chip fill colors are non-semantic; the semantic signal is the rendered category label and slot label text.
