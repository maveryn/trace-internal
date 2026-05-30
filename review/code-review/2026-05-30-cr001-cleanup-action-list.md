# CR-001 Cleanup Action List

Date: 2026-05-30

This action list converts the dirty-tree triage into file-level recommendations. It does not stage, delete, restore, or revert source-like files.

## Decisions

- Tracked deleted files: `52` -> keep deletions. All deleted task docs/config examples are inactive task ids; deleted illustration code/test paths have no active import references in the current active surface.
- Untracked source-like files: `153` -> keep/stage with the current change set. Active task-doc check found `0` inactive untracked task docs, and example-config check found `0` inactive untracked example configs.
- Tracked modified files: `1037` -> do not revert blindly. Split into intentional change sets before commit/release.

## Tracked Deleted Files

- keep deletion: `configs/examples/task_icons__pair_grid__pair_geometric_transform_count.yaml` (retired `task_icons__pair_grid__pair_geometric_transform_count`)
- keep deletion: `configs/examples/task_icons__paired_canvas__panel_difference_count.yaml` (retired `task_icons__paired_canvas__panel_difference_count`)
- keep deletion: `configs/examples/task_icons__paired_canvas__panel_exact_match_count.yaml` (retired `task_icons__paired_canvas__panel_exact_match_count`)
- keep deletion: `configs/examples/task_icons__pattern_grid__color_pattern_violation_index.yaml` (retired `task_icons__pattern_grid__color_pattern_violation_index`)
- keep deletion: `configs/examples/task_icons__pattern_grid__size_pattern_violation_index.yaml` (retired `task_icons__pattern_grid__size_pattern_violation_index`)
- keep deletion: `configs/examples/task_icons__reference_canvas__attribute_match_count.yaml` (retired `task_icons__reference_canvas__attribute_match_count`)
- keep deletion: `configs/examples/task_icons__reference_canvas__size_relation_count.yaml` (retired `task_icons__reference_canvas__size_relation_count`)
- keep deletion: `docs/tasks/task_charts__region_map__border_neighbor_count.md` (retired `task_charts__region_map__border_neighbor_count`)
- keep deletion: `docs/tasks/task_games__crossing__safe_route_label.md` (retired `task_games__crossing__safe_route_label`)
- keep deletion: `docs/tasks/task_games__minecraft__resource_route_cost_value.md` (retired `task_games__minecraft__resource_route_cost_value`)
- keep deletion: `docs/tasks/task_games__minecraft__tunnel_clearance_count.md` (retired `task_games__minecraft__tunnel_clearance_count`)
- keep deletion: `docs/tasks/task_geometry__area_partition__parallelogram_area_partition_total_area_value.md` (retired `task_geometry__area_partition__parallelogram_area_partition_total_area_value`)
- keep deletion: `docs/tasks/task_geometry__area_partition__triangle_area_partition_total_area_value.md` (retired `task_geometry__area_partition__triangle_area_partition_total_area_value`)
- keep deletion: `docs/tasks/task_graph__binary_tree__tree_operation_label.md` (retired `task_graph__binary_tree__tree_operation_label`)
- keep deletion: `docs/tasks/task_icons__named_field__shape_pair_difference_count.md` (retired `task_icons__named_field__shape_pair_difference_count`)
- keep deletion: `docs/tasks/task_icons__named_field__shape_pair_total_count.md` (retired `task_icons__named_field__shape_pair_total_count`)
- keep deletion: `docs/tasks/task_icons__pair_grid__pair_attribute_rule_count.md` (retired `task_icons__pair_grid__pair_attribute_rule_count`)
- keep deletion: `docs/tasks/task_icons__pair_grid__pair_geometric_transform_count.md` (retired `task_icons__pair_grid__pair_geometric_transform_count`)
- keep deletion: `docs/tasks/task_icons__paired_canvas__panel_difference_count.md` (retired `task_icons__paired_canvas__panel_difference_count`)
- keep deletion: `docs/tasks/task_icons__paired_canvas__panel_exact_match_count.md` (retired `task_icons__paired_canvas__panel_exact_match_count`)
- keep deletion: `docs/tasks/task_icons__pattern_grid__color_pattern_violation_index.md` (retired `task_icons__pattern_grid__color_pattern_violation_index`)
- keep deletion: `docs/tasks/task_icons__pattern_grid__size_pattern_violation_index.md` (retired `task_icons__pattern_grid__size_pattern_violation_index`)
- keep deletion: `docs/tasks/task_icons__reference_canvas__attribute_match_count.md` (retired `task_icons__reference_canvas__attribute_match_count`)
- keep deletion: `docs/tasks/task_icons__reference_canvas__size_relation_count.md` (retired `task_icons__reference_canvas__size_relation_count`)
- keep deletion: `docs/tasks/task_illustrations__construction_site__material_stack_count.md` (retired `task_illustrations__construction_site__material_stack_count`)
- keep deletion: `docs/tasks/task_illustrations__indoor_room__container_object_count.md` (retired `task_illustrations__indoor_room__container_object_count`)
- keep deletion: `docs/tasks/task_illustrations__market__customer_at_shop_count.md` (retired `task_illustrations__market__customer_at_shop_count`)
- keep deletion: `docs/tasks/task_illustrations__market__shop_attribute_count.md` (retired `task_illustrations__market__shop_attribute_count`)
- keep deletion: `docs/tasks/task_pages__concept_map__branch_item_count.md` (retired `task_pages__concept_map__branch_item_count`)
- keep deletion: `docs/tasks/task_pages__concept_map__filtered_node_count.md` (retired `task_pages__concept_map__filtered_node_count`)
- keep deletion: `docs/tasks/task_pages__control_board__filter_count.md` (retired `task_pages__control_board__filter_count`)
- keep deletion: `docs/tasks/task_pages__hierarchy__tree_count.md` (retired `task_pages__hierarchy__tree_count`)
- keep deletion: `docs/tasks/task_pages__infographic__column_profile_comparison_value.md` (retired `task_pages__infographic__column_profile_comparison_value`)
- keep deletion: `docs/tasks/task_pages__infographic__filtered_metric_total_value.md` (retired `task_pages__infographic__filtered_metric_total_value`)
- keep deletion: `docs/tasks/task_pages__infographic__filtered_section_extremum_label.md` (retired `task_pages__infographic__filtered_section_extremum_label`)
- keep deletion: `docs/tasks/task_pages__infographic__section_ranked_total_label.md` (retired `task_pages__infographic__section_ranked_total_label`)
- keep deletion: `docs/tasks/task_pages__schedule__longer_than_reference_count.md` (retired `task_pages__schedule__longer_than_reference_count`)
- keep deletion: `docs/tasks/task_pages__schedule__overlap_count.md` (retired `task_pages__schedule__overlap_count`)
- keep deletion: `docs/tasks/task_physics__paired_resistor__missing_resistor_value.md` (retired `task_physics__paired_resistor__missing_resistor_value`)
- keep deletion: `docs/tasks/task_physics__resistor__total_resistance_value.md` (retired `task_physics__resistor__total_resistance_value`)
- keep deletion: `docs/tasks/task_puzzles__voxel_ladder__voxel_ladder_route_count.md` (retired `task_puzzles__voxel_ladder__voxel_ladder_route_count`)
- keep deletion: `docs/tasks/task_puzzles__voxel_ladder__voxel_ladder_route_label.md` (retired `task_puzzles__voxel_ladder__voxel_ladder_route_label`)
- keep deletion: `tests/test_illustrations_urban_market_tasks.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/_market_shop_category_branch.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/_market_shop_color_branch.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/_market_shop_selling_branch.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/container_object_count.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/customer_at_shop_type_count.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/market_shop_attribute_count.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/counting/material_stack_type_count.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/shared/urban_market_rendering.py` (retired inactive illustration surface; no active import references found)
- keep deletion: `trace/tasks/illustrations/shared/urban_market_scene.py` (retired inactive illustration surface; no active import references found)

## Untracked Source-Like Files

- keep/stage: `docs/tasks/task_charts__annotated_series__callout_endpoint_change_value.md` (active `task_charts__annotated_series__callout_endpoint_change_value`)
- keep/stage: `docs/tasks/task_charts__annotated_series__event_window_extremum_label.md` (active `task_charts__annotated_series__event_window_extremum_label`)
- keep/stage: `docs/tasks/task_charts__annotated_series__event_window_threshold_count.md` (active `task_charts__annotated_series__event_window_threshold_count`)
- keep/stage: `docs/tasks/task_charts__dashboard__category_panel_condition_count.md` (active `task_charts__dashboard__category_panel_condition_count`)
- keep/stage: `docs/tasks/task_charts__dashboard__top_k_overlap_count.md` (active `task_charts__dashboard__top_k_overlap_count`)
- keep/stage: `docs/tasks/task_charts__radial_progress__extremum_remaining_label.md` (active `task_charts__radial_progress__extremum_remaining_label`)
- keep/stage: `docs/tasks/task_charts__region_map__group_filtered_region_value.md` (active `task_charts__region_map__group_filtered_region_value`)
- keep/stage: `docs/tasks/task_charts__region_map__named_region_set_total_value.md` (active `task_charts__region_map__named_region_set_total_value`)
- keep/stage: `docs/tasks/task_games__minecraft__route_block_count.md` (active `task_games__minecraft__route_block_count`)
- keep/stage: `docs/tasks/task_games__rule_override_board__line_result_count.md` (active `task_games__rule_override_board__line_result_count`)
- keep/stage: `docs/tasks/task_games__rule_override_board__piece_result_count.md` (active `task_games__rule_override_board__piece_result_count`)
- keep/stage: `docs/tasks/task_geometry__area_partition__total_area_value.md` (active `task_geometry__area_partition__total_area_value`)
- keep/stage: `docs/tasks/task_geometry__bearing_route__endpoint_position_label.md` (active `task_geometry__bearing_route__endpoint_position_label`)
- keep/stage: `docs/tasks/task_geometry__bearing_route__final_displacement_value.md` (active `task_geometry__bearing_route__final_displacement_value`)
- keep/stage: `docs/tasks/task_geometry__cylinder_wrap__surface_path_length_value.md` (active `task_geometry__cylinder_wrap__surface_path_length_value`)
- keep/stage: `docs/tasks/task_geometry__cylinder_wrap__wrapped_mark_position_label.md` (active `task_geometry__cylinder_wrap__wrapped_mark_position_label`)
- keep/stage: `docs/tasks/task_geometry__measuring_tools__protractor_angle_value.md` (active `task_geometry__measuring_tools__protractor_angle_value`)
- keep/stage: `docs/tasks/task_geometry__measuring_tools__ruler_length_value.md` (active `task_geometry__measuring_tools__ruler_length_value`)
- keep/stage: `docs/tasks/task_graph__binary_tree__bst_path_operation_label.md` (active `task_graph__binary_tree__bst_path_operation_label`)
- keep/stage: `docs/tasks/task_graph__binary_tree__heap_property_violation_label.md` (active `task_graph__binary_tree__heap_property_violation_label`)
- keep/stage: `docs/tasks/task_icons__icon_cutout__partial_match_label.md` (active `task_icons__icon_cutout__partial_match_label`)
- keep/stage: `docs/tasks/task_icons__named_field__shape_pair_arithmetic_count.md` (active `task_icons__named_field__shape_pair_arithmetic_count`)
- keep/stage: `docs/tasks/task_icons__named_grid__line_condition_count.md` (active `task_icons__named_grid__line_condition_count`)
- keep/stage: `docs/tasks/task_icons__named_grid__row_column_shape_count.md` (active `task_icons__named_grid__row_column_shape_count`)
- keep/stage: `docs/tasks/task_icons__named_grid__row_column_shape_extreme_number.md` (active `task_icons__named_grid__row_column_shape_extreme_number`)
- keep/stage: `docs/tasks/task_icons__named_path__path_neighbor_label.md` (active `task_icons__named_path__path_neighbor_label`)
- keep/stage: `docs/tasks/task_icons__named_ring__arc_shape_count.md` (active `task_icons__named_ring__arc_shape_count`)
- keep/stage: `docs/tasks/task_icons__named_strip__shape_run_length.md` (active `task_icons__named_strip__shape_run_length`)
- keep/stage: `docs/tasks/task_icons__pair_grid__pair_relation_count.md` (active `task_icons__pair_grid__pair_relation_count`)
- keep/stage: `docs/tasks/task_icons__paired_canvas__panel_set_relation_count.md` (active `task_icons__paired_canvas__panel_set_relation_count`)
- keep/stage: `docs/tasks/task_icons__pattern_grid__attribute_pattern_violation_index.md` (active `task_icons__pattern_grid__attribute_pattern_violation_index`)
- keep/stage: `docs/tasks/task_icons__reference_canvas__reference_predicate_count.md` (active `task_icons__reference_canvas__reference_predicate_count`)
- keep/stage: `docs/tasks/task_pages__concept_map__node_filter_count.md` (active `task_pages__concept_map__node_filter_count`)
- keep/stage: `docs/tasks/task_pages__control_board__control_filter_count.md` (active `task_pages__control_board__control_filter_count`)
- keep/stage: `docs/tasks/task_pages__data_table__row_filter_count.md` (active `task_pages__data_table__row_filter_count`)
- keep/stage: `docs/tasks/task_pages__hierarchy__path_length_count.md` (active `task_pages__hierarchy__path_length_count`)
- keep/stage: `docs/tasks/task_pages__hierarchy__subtree_node_count.md` (active `task_pages__hierarchy__subtree_node_count`)
- keep/stage: `docs/tasks/task_pages__infographic__fact_lookup_label.md` (active `task_pages__infographic__fact_lookup_label`)
- keep/stage: `docs/tasks/task_pages__infographic__section_rank_label.md` (active `task_pages__infographic__section_rank_label`)
- keep/stage: `docs/tasks/task_pages__profile_card_grid__attribute_lookup_label.md` (active `task_pages__profile_card_grid__attribute_lookup_label`)
- keep/stage: `docs/tasks/task_pages__ranked_list__ordinal_entry_label.md` (active `task_pages__ranked_list__ordinal_entry_label`)
- keep/stage: `docs/tasks/task_pages__schedule__reference_interval_count.md` (active `task_pages__schedule__reference_interval_count`)
- keep/stage: `docs/tasks/task_pages__step_list__ordinal_step_detail_label.md` (active `task_pages__step_list__ordinal_step_detail_label`)
- keep/stage: `docs/tasks/task_physics__circuit_equivalent__total_capacitance_value.md` (active `task_physics__circuit_equivalent__total_capacitance_value`)
- keep/stage: `docs/tasks/task_physics__circuit_equivalent__total_resistance_value.md` (active `task_physics__circuit_equivalent__total_resistance_value`)
- keep/stage: `docs/tasks/task_puzzles__cube_net__surface_net_path_label.md` (active `task_puzzles__cube_net__surface_net_path_label`)
- keep/stage: `docs/tasks/task_puzzles__toggle_grid__toggle_repair_switch_label.md` (active `task_puzzles__toggle_grid__toggle_repair_switch_label`)
- keep/stage: `docs/tasks/task_puzzles__toggle_grid__toggle_result_label.md` (active `task_puzzles__toggle_grid__toggle_result_label`)
- keep/stage: `docs/tasks/task_puzzles__voxel_ladder__checkpoint_reachability.md` (active `task_puzzles__voxel_ladder__checkpoint_reachability`)
- keep/stage: `docs/tasks/task_puzzles__voxel_ladder__checkpoint_sequence_label.md` (active `task_puzzles__voxel_ladder__checkpoint_sequence_label`)
- keep/stage: `docs/tasks/task_three_d__object_scene__counterfactual_attribute_count.md` (active `task_three_d__object_scene__counterfactual_attribute_count`)
- keep/stage: `docs/tasks/task_three_d__object_scene__multiview_object_match_label.md` (active `task_three_d__object_scene__multiview_object_match_label`)
- keep/stage: `docs/tasks/task_three_d__object_scene__named_object_count.md` (active `task_three_d__object_scene__named_object_count`)
- keep/stage: `docs/tasks/task_three_d__object_scene__spatial_relation_count.md` (active `task_three_d__object_scene__spatial_relation_count`)
- keep/stage: `docs/tasks/task_three_d__object_scene__view_relation_count.md` (active `task_three_d__object_scene__view_relation_count`)
- keep/stage: `configs/examples/task_icons__pair_grid__pair_relation_count.yaml` (active `task_icons__pair_grid__pair_relation_count`)
- keep/stage: `configs/examples/task_icons__paired_canvas__panel_set_relation_count.yaml` (active `task_icons__paired_canvas__panel_set_relation_count`)
- keep/stage: `configs/examples/task_icons__pattern_grid__attribute_pattern_violation_index.yaml` (active `task_icons__pattern_grid__attribute_pattern_violation_index`)
- keep/stage: `configs/examples/task_icons__reference_canvas__reference_predicate_count.yaml` (active `task_icons__reference_canvas__reference_predicate_count`)
- keep/stage or review with owning change set: `assets/fonts/readout_pool_v0.json`
- keep/stage or review with owning change set: `configs/domains/charts/annotated_series.yaml`
- keep/stage or review with owning change set: `configs/domains/games/rule_override_board.yaml`
- keep/stage or review with owning change set: `configs/domains/pages/document_lookup.yaml`
- keep/stage or review with owning change set: `configs/domains/pages/step_list.yaml`
- keep/stage or review with owning change set: `docs/workflows/TASK_REVIEW_WEB_APP.md`
- keep/stage or review with owning change set: `prompts/charts/annotated_series/charts_annotated_series_v0.json`
- keep/stage or review with owning change set: `prompts/games/rule_override_board/games_rule_override_board_v0.json`
- keep/stage or review with owning change set: `prompts/geometry/measurement/geometry_bearing_route_v0.json`
- keep/stage or review with owning change set: `prompts/geometry/measurement/geometry_cylinder_wrap_v0.json`
- keep/stage or review with owning change set: `prompts/geometry/measurement/geometry_measuring_tools_v0.json`
- keep/stage or review with owning change set: `prompts/pages/document_lookup/pages_document_lookup_v0.json`
- keep/stage or review with owning change set: `prompts/pages/step_list/pages_step_list_v0.json`
- keep/stage or review with owning change set: `scripts/audit_text_legibility.py`
- keep/stage or review with owning change set: `scripts/generate_icon_resource_spritesheets.py`
- keep/stage or review with owning change set: `scripts/generate_readout_font_spritesheet.py`
- keep/stage or review with owning change set: `scripts/generate_three_d_object_spritesheets.py`
- keep/stage or review with owning change set: `scripts/run_review_app.py`
- keep/stage or review with owning change set: `tests/test_charts_annotated_series_tasks.py`
- keep/stage or review with owning change set: `tests/test_charts_radar_tasks.py`
- keep/stage or review with owning change set: `tests/test_games_rule_override_board_tasks.py`
- keep/stage or review with owning change set: `tests/test_geometry_bearing_route_tasks.py`
- keep/stage or review with owning change set: `tests/test_geometry_cylinder_wrap_tasks.py`
- keep/stage or review with owning change set: `tests/test_graph_evidence_answer_consistency.py`
- keep/stage or review with owning change set: `tests/test_graph_query_specific_evidence_prompts.py`
- keep/stage or review with owning change set: `tests/test_graph_relation_structure_match_label_tasks.py`
- keep/stage or review with owning change set: `tests/test_icons_counting_named_grid_line_condition_count.py`
- keep/stage or review with owning change set: `tests/test_icons_counting_named_grid_row_column_shape_count.py`
- keep/stage or review with owning change set: `tests/test_icons_counting_named_grid_row_column_shape_extreme_number.py`
- keep/stage or review with owning change set: `tests/test_icons_counting_named_ring_arc_shape_count.py`
- keep/stage or review with owning change set: `tests/test_icons_relation_named_path_neighbor_label_tasks.py`
- keep/stage or review with owning change set: `tests/test_icons_relation_partial_match_label_tasks.py`
- keep/stage or review with owning change set: `tests/test_icons_sequence_named_shape_run_length_tasks.py`
- keep/stage or review with owning change set: `tests/test_illustrations_construction_site_tasks.py`
- keep/stage or review with owning change set: `tests/test_pages_document_lookup_tasks.py`
- keep/stage or review with owning change set: `tests/test_pages_step_list_tasks.py`
- keep/stage or review with owning change set: `tests/test_puzzles_counterfactual_board_grid_count.py`
- keep/stage or review with owning change set: `tests/test_puzzles_logic_toggle_grid_tasks.py`
- keep/stage or review with owning change set: `tests/test_puzzles_matchstick_tasks.py`
- keep/stage or review with owning change set: `tests/test_review_app.py`
- keep/stage or review with owning change set: `tests/test_reward_scoring.py`
- keep/stage or review with owning change set: `tests/test_shared_render_variation_layout_jitter.py`
- keep/stage or review with owning change set: `tests/test_text_legibility.py`
- keep/stage or review with owning change set: `tests/test_three_d_spatial_counterfactual_attribute_count.py`
- keep/stage or review with owning change set: `tests/test_three_d_spatial_multiview_object_match.py`
- keep/stage or review with owning change set: `tests/test_three_d_spatial_named_object_count.py`
- keep/stage or review with owning change set: `tests/test_three_d_spatial_relation_count.py`
- keep/stage or review with owning change set: `tests/test_three_d_spatial_view_relation_count.py`
- keep/stage or review with owning change set: `trace/core/reward_scoring.py`
- keep/stage or review with owning change set: `trace/review_app/__init__.py`
- keep/stage or review with owning change set: `trace/review_app/artifact_index.py`
- keep/stage or review with owning change set: `trace/review_app/feedback.py`
- keep/stage or review with owning change set: `trace/review_app/models.py`
- keep/stage or review with owning change set: `trace/review_app/resource_index.py`
- keep/stage or review with owning change set: `trace/review_app/server.py`
- keep/stage or review with owning change set: `trace/review_app/static/app.css`
- keep/stage or review with owning change set: `trace/review_app/static/app.js`
- keep/stage or review with owning change set: `trace/review_app/templates/base.html`
- keep/stage or review with owning change set: `trace/review_app/templates/domain.html`
- keep/stage or review with owning change set: `trace/review_app/templates/index.html`
- keep/stage or review with owning change set: `trace/review_app/templates/login.html`
- keep/stage or review with owning change set: `trace/review_app/templates/resources.html`
- keep/stage or review with owning change set: `trace/review_app/templates/sample.html`
- keep/stage or review with owning change set: `trace/review_app/templates/scene.html`
- keep/stage or review with owning change set: `trace/review_app/templates/search.html`
- keep/stage or review with owning change set: `trace/review_app/templates/task.html`
- keep/stage or review with owning change set: `trace/tasks/charts/annotated_series/__init__.py`
- keep/stage or review with owning change set: `trace/tasks/charts/annotated_series/event_window_query.py`
- keep/stage or review with owning change set: `trace/tasks/games/rule_override_board/__init__.py`
- keep/stage or review with owning change set: `trace/tasks/games/rule_override_board/board_tasks.py`
- keep/stage or review with owning change set: `trace/tasks/geometry/measurement/bearing_route.py`
- keep/stage or review with owning change set: `trace/tasks/geometry/measurement/cylinder_wrap.py`
- keep/stage or review with owning change set: `trace/tasks/geometry/measurement/measuring_tools.py`
- keep/stage or review with owning change set: `trace/tasks/icons/counting/named_grid_line_condition_count.py`
- keep/stage or review with owning change set: `trace/tasks/icons/counting/named_grid_row_column_shape_count.py`
- keep/stage or review with owning change set: `trace/tasks/icons/counting/named_grid_row_column_shape_extreme_number.py`
- keep/stage or review with owning change set: `trace/tasks/icons/counting/named_ring_arc_shape_count.py`
- keep/stage or review with owning change set: `trace/tasks/icons/counting/panel_set_relation_count.py`
- keep/stage or review with owning change set: `trace/tasks/icons/relation/named_path_neighbor_label.py`
- keep/stage or review with owning change set: `trace/tasks/icons/relation/partial_match_label.py`
- keep/stage or review with owning change set: `trace/tasks/icons/sequence/named_shape_run_length.py`
- keep/stage or review with owning change set: `trace/tasks/icons/shared/scene_style.py`
- keep/stage or review with owning change set: `trace/tasks/pages/document_lookup/__init__.py`
- keep/stage or review with owning change set: `trace/tasks/pages/document_lookup/card_and_list_lookup.py`
- keep/stage or review with owning change set: `trace/tasks/pages/shared/render_audit_defaults.py`
- keep/stage or review with owning change set: `trace/tasks/pages/step_list/__init__.py`
- keep/stage or review with owning change set: `trace/tasks/pages/step_list/ordinal_step_detail_label.py`
- keep/stage or review with owning change set: `trace/tasks/puzzles/logic/toggle_grid.py`
- keep/stage or review with owning change set: `trace/tasks/shared/text_legibility.py`
- keep/stage or review with owning change set: `trace/tasks/three_d/spatial/counterfactual_attribute_count.py`
- keep/stage or review with owning change set: `trace/tasks/three_d/spatial/multiview_object_match.py`
- keep/stage or review with owning change set: `trace/tasks/three_d/spatial/named_object_count.py`
- keep/stage or review with owning change set: `trace/tasks/three_d/spatial/spatial_relation_count.py`
- keep/stage or review with owning change set: `trace/tasks/three_d/spatial/view_relation_count.py`

## Tracked Modified Summary

| Root | Count |
| --- | ---: |
| `.gitignore` | 1 |
| `AGENTS.md` | 1 |
| `README.md` | 1 |
| `assets` | 2 |
| `configs` | 108 |
| `docs` | 289 |
| `prompts` | 81 |
| `pyproject.toml` | 1 |
| `scripts` | 19 |
| `skills` | 6 |
| `tests` | 200 |
| `trace` | 328 |

## Next Gate

CR-001 can be marked resolved only after these keep/delete/revert decisions are represented in a clean commit or an explicitly approved cleanup patch.
