# Dirty Tree Triage

Date: 2026-05-30

This manifest categorizes current dirty working-tree state after automatic removal of cache directories, notebook checkpoint directories, and Python bytecode under active source/review roots. It does not approve deletion or reversion of source-like files.

## Summary

| Category | Count |
| --- | ---: |
| `generated_review_artifacts_manual_keep_or_refresh` | 1 |
| `persistent_review_workspace_changes` | 6 |
| `tracked_deleted_needs_file_level_decision` | 52 |
| `tracked_modified_needs_file_level_decision` | 1037 |
| `untracked_source_like_needs_file_level_decision` | 153 |

## Required Follow-Up

- `tracked_modified_needs_file_level_decision`: review, stage, or explicitly approve revert for each file.
- `tracked_deleted_needs_file_level_decision`: confirm whether each deletion is intentional before restoring or committing.
- `untracked_source_like_needs_file_level_decision`: confirm whether each file should be kept/staged or deleted.
- `persistent_review_workspace_changes`: expected for this maintenance-review work unless the corresponding report is superseded.
- `generated_review_artifacts_manual_keep_or_refresh`: keep only if still useful for inspection; otherwise regenerate under the current review workflow.

## Category Samples

### `generated_review_artifacts_manual_keep_or_refresh` (1)
- `??` `review/task-reviews/README.md`

### `persistent_review_workspace_changes` (6)
- `??` `review/code-review/2026-05-30-dirty-tree-triage.json`
- `??` `review/code-review/2026-05-30-dirty-tree-triage.md`
- `??` `review/code-review/2026-05-30-full-codebase-maintenance-review.json`
- `??` `review/code-review/2026-05-30-full-codebase-maintenance-review.md`
- `??` `review/docs/CALIBRATION_GUIDE.md`
- `??` `review/docs/README.md`

### `tracked_deleted_needs_file_level_decision` (52)
- ` D` `configs/examples/task_icons__pair_grid__pair_geometric_transform_count.yaml`
- ` D` `configs/examples/task_icons__paired_canvas__panel_difference_count.yaml`
- ` D` `configs/examples/task_icons__paired_canvas__panel_exact_match_count.yaml`
- ` D` `configs/examples/task_icons__pattern_grid__color_pattern_violation_index.yaml`
- ` D` `configs/examples/task_icons__pattern_grid__size_pattern_violation_index.yaml`
- ` D` `configs/examples/task_icons__reference_canvas__attribute_match_count.yaml`
- ` D` `configs/examples/task_icons__reference_canvas__size_relation_count.yaml`
- ` D` `docs/tasks/task_charts__region_map__border_neighbor_count.md`
- ` D` `docs/tasks/task_games__crossing__safe_route_label.md`
- ` D` `docs/tasks/task_games__minecraft__resource_route_cost_value.md`
- ` D` `docs/tasks/task_games__minecraft__tunnel_clearance_count.md`
- ` D` `docs/tasks/task_geometry__area_partition__parallelogram_area_partition_total_area_value.md`
- ` D` `docs/tasks/task_geometry__area_partition__triangle_area_partition_total_area_value.md`
- ` D` `docs/tasks/task_graph__binary_tree__tree_operation_label.md`
- ` D` `docs/tasks/task_icons__named_field__shape_pair_difference_count.md`
- ` D` `docs/tasks/task_icons__named_field__shape_pair_total_count.md`
- ` D` `docs/tasks/task_icons__pair_grid__pair_attribute_rule_count.md`
- ` D` `docs/tasks/task_icons__pair_grid__pair_geometric_transform_count.md`
- ` D` `docs/tasks/task_icons__paired_canvas__panel_difference_count.md`
- ` D` `docs/tasks/task_icons__paired_canvas__panel_exact_match_count.md`
- ` D` `docs/tasks/task_icons__pattern_grid__color_pattern_violation_index.md`
- ` D` `docs/tasks/task_icons__pattern_grid__size_pattern_violation_index.md`
- ` D` `docs/tasks/task_icons__reference_canvas__attribute_match_count.md`
- ` D` `docs/tasks/task_icons__reference_canvas__size_relation_count.md`
- ` D` `docs/tasks/task_illustrations__construction_site__material_stack_count.md`
- ` D` `docs/tasks/task_illustrations__indoor_room__container_object_count.md`
- ` D` `docs/tasks/task_illustrations__market__customer_at_shop_count.md`
- ` D` `docs/tasks/task_illustrations__market__shop_attribute_count.md`
- ` D` `docs/tasks/task_pages__concept_map__branch_item_count.md`
- ` D` `docs/tasks/task_pages__concept_map__filtered_node_count.md`
- ` D` `docs/tasks/task_pages__control_board__filter_count.md`
- ` D` `docs/tasks/task_pages__hierarchy__tree_count.md`
- ` D` `docs/tasks/task_pages__infographic__column_profile_comparison_value.md`
- ` D` `docs/tasks/task_pages__infographic__filtered_metric_total_value.md`
- ` D` `docs/tasks/task_pages__infographic__filtered_section_extremum_label.md`
- ` D` `docs/tasks/task_pages__infographic__section_ranked_total_label.md`
- ` D` `docs/tasks/task_pages__schedule__longer_than_reference_count.md`
- ` D` `docs/tasks/task_pages__schedule__overlap_count.md`
- ` D` `docs/tasks/task_physics__paired_resistor__missing_resistor_value.md`
- ` D` `docs/tasks/task_physics__resistor__total_resistance_value.md`
- ... 12 more entries in JSON manifest

### `tracked_modified_needs_file_level_decision` (1037)
- ` M` `.gitignore`
- ` M` `AGENTS.md`
- ` M` `README.md`
- ` M` `assets/fonts/README.md`
- ` M` `assets/labels/README.md`
- ` M` `configs/domains/charts/area.yaml`
- ` M` `configs/domains/charts/candlestick.yaml`
- ` M` `configs/domains/charts/combo.yaml`
- ` M` `configs/domains/charts/composition.yaml`
- ` M` `configs/domains/charts/dashboard.yaml`
- ` M` `configs/domains/charts/distribution.yaml`
- ` M` `configs/domains/charts/dumbbell.yaml`
- ` M` `configs/domains/charts/error_interval.yaml`
- ` M` `configs/domains/charts/flow.yaml`
- ` M` `configs/domains/charts/map.yaml`
- ` M` `configs/domains/charts/matrix.yaml`
- ` M` `configs/domains/charts/multiseries.yaml`
- ` M` `configs/domains/charts/parallel_coordinates.yaml`
- ` M` `configs/domains/charts/pictogram.yaml`
- ` M` `configs/domains/charts/radar.yaml`
- ` M` `configs/domains/charts/radial_progress.yaml`
- ` M` `configs/domains/charts/scatter.yaml`
- ` M` `configs/domains/charts/scientific.yaml`
- ` M` `configs/domains/charts/size_encoding.yaml`
- ` M` `configs/domains/charts/three_d.yaml`
- ` M` `configs/domains/charts/trend.yaml`
- ` M` `configs/domains/charts/waterfall.yaml`
- ` M` `configs/domains/games/2048.yaml`
- ` M` `configs/domains/games/backgammon.yaml`
- ` M` `configs/domains/games/base.yaml`
- ` M` `configs/domains/games/bingo.yaml`
- ` M` `configs/domains/games/bowling.yaml`
- ` M` `configs/domains/games/brick_breaker.yaml`
- ` M` `configs/domains/games/bubble_shooter.yaml`
- ` M` `configs/domains/games/cards.yaml`
- ` M` `configs/domains/games/checkers.yaml`
- ` M` `configs/domains/games/chess.yaml`
- ` M` `configs/domains/games/chess_variant.yaml`
- ` M` `configs/domains/games/connect_four.yaml`
- ` M` `configs/domains/games/crossing.yaml`
- ... 997 more entries in JSON manifest

### `untracked_source_like_needs_file_level_decision` (153)
- `??` `assets/fonts/readout_pool_v0.json`
- `??` `configs/domains/charts/annotated_series.yaml`
- `??` `configs/domains/games/rule_override_board.yaml`
- `??` `configs/domains/pages/document_lookup.yaml`
- `??` `configs/domains/pages/step_list.yaml`
- `??` `configs/examples/task_icons__pair_grid__pair_relation_count.yaml`
- `??` `configs/examples/task_icons__paired_canvas__panel_set_relation_count.yaml`
- `??` `configs/examples/task_icons__pattern_grid__attribute_pattern_violation_index.yaml`
- `??` `configs/examples/task_icons__reference_canvas__reference_predicate_count.yaml`
- `??` `docs/tasks/task_charts__annotated_series__callout_endpoint_change_value.md`
- `??` `docs/tasks/task_charts__annotated_series__event_window_extremum_label.md`
- `??` `docs/tasks/task_charts__annotated_series__event_window_threshold_count.md`
- `??` `docs/tasks/task_charts__dashboard__category_panel_condition_count.md`
- `??` `docs/tasks/task_charts__dashboard__top_k_overlap_count.md`
- `??` `docs/tasks/task_charts__radial_progress__extremum_remaining_label.md`
- `??` `docs/tasks/task_charts__region_map__group_filtered_region_value.md`
- `??` `docs/tasks/task_charts__region_map__named_region_set_total_value.md`
- `??` `docs/tasks/task_games__minecraft__route_block_count.md`
- `??` `docs/tasks/task_games__rule_override_board__line_result_count.md`
- `??` `docs/tasks/task_games__rule_override_board__piece_result_count.md`
- `??` `docs/tasks/task_geometry__area_partition__total_area_value.md`
- `??` `docs/tasks/task_geometry__bearing_route__endpoint_position_label.md`
- `??` `docs/tasks/task_geometry__bearing_route__final_displacement_value.md`
- `??` `docs/tasks/task_geometry__cylinder_wrap__surface_path_length_value.md`
- `??` `docs/tasks/task_geometry__cylinder_wrap__wrapped_mark_position_label.md`
- `??` `docs/tasks/task_geometry__measuring_tools__protractor_angle_value.md`
- `??` `docs/tasks/task_geometry__measuring_tools__ruler_length_value.md`
- `??` `docs/tasks/task_graph__binary_tree__bst_path_operation_label.md`
- `??` `docs/tasks/task_graph__binary_tree__heap_property_violation_label.md`
- `??` `docs/tasks/task_icons__icon_cutout__partial_match_label.md`
- `??` `docs/tasks/task_icons__named_field__shape_pair_arithmetic_count.md`
- `??` `docs/tasks/task_icons__named_grid__line_condition_count.md`
- `??` `docs/tasks/task_icons__named_grid__row_column_shape_count.md`
- `??` `docs/tasks/task_icons__named_grid__row_column_shape_extreme_number.md`
- `??` `docs/tasks/task_icons__named_path__path_neighbor_label.md`
- `??` `docs/tasks/task_icons__named_ring__arc_shape_count.md`
- `??` `docs/tasks/task_icons__named_strip__shape_run_length.md`
- `??` `docs/tasks/task_icons__pair_grid__pair_relation_count.md`
- `??` `docs/tasks/task_icons__paired_canvas__panel_set_relation_count.md`
- `??` `docs/tasks/task_icons__pattern_grid__attribute_pattern_violation_index.md`
- ... 113 more entries in JSON manifest
