# Calibration Progress Summary

This file is the task-level current-best index for the manual TRACE difficulty calibration pass.

Only record numbers here when they were obtained with the current code/config, or with an explicit config override documented in the task record. Do not copy historical `Qwen/Qwen3-VL-2B-Instruct` reference numbers or stale `200 x 32` measurements into this file.

Current standard:

- model: `Qwen/Qwen3-VL-8B-Instruct`
- samples: `100`
- rollouts per prompt: `64`
- backend: `vLLM`
- easy sample: `solved_rollouts >= 58`
- hard sample: `solved_rollouts == 0`
- target: `easy_frac <= 0.15` and `hard_frac <= 0.15`

Column guide:

- `Best status`: `pending_current_probe`, `distribution_failed`, `probed`, `accepted`, `blocked`, or `dropped`.
- `Best config`: short label for the retained current-code/current-config support.
- `Hard/Easy/Band`: fractions from the retained `100 x 64` probe.
- `Artifacts`: exact parquet, review workbook, and model-output references when available.

## Charts

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_charts_composition_subset_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_counting_value_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_distribution_boxplot_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_distribution_density_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_distribution_histogram_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_multiseries_pairwise_comparison_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_readout_subset_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_statistics_summary_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_statistics_summary_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_charts_trend_structure_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Diagrams

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_diagrams_cycle_offset_stage_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_diagrams_flow_next_step_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_diagrams_hierarchy_ancestor_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_diagrams_schematic_callout_target_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_diagrams_set_diagram_region_sum_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Documents

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_documents_arithmetic_section_expression_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_documents_layout_section_membership_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_documents_readout_field_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_documents_relation_section_extremum_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_documents_selection_checkbox_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Games

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_games_bingo_completed_line_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_cards_hand_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_checkers_move_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_connect_four_move_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_dominoes_chain_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_dots_and_boxes_capture_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_go_group_liberty_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_mancala_move_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_nine_mens_morris_pieces_in_mill_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_games_reversi_move_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Geometry

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_geometry_analytical_2d_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_analytical_3d_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_comparison_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_coordinate_relation` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_counting_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_graphing_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_measurement_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_similarity_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_solid_view_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_geometry_transformation_match` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Graph

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_graph_comparison_largest_component_size` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_counting_articulation_point_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_counting_bridge_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_counting_degree_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_optimization_minimum_spanning_tree_weight` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_order_topological_position` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_path_shortest_path_length` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_relation_reachable_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_relation_same_component_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_graph_relation_unique_cycle_size` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Icons

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_icons_counting_reference_match_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_counting_singleton_type` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_counting_size_relation` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_pattern_structured_violation` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_relation_between_two_anchors_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_relation_mirror_symmetry` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_relation_occlusion_order` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_relation_relative_position_type` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_sequence_missing_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_icons_transformation_pair_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Physics

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_physics_circuits_equivalent_resistance` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_physics_mechanics_force_diagram` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_physics_mechanics_lever_balance` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_physics_mechanics_spring_extension` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_physics_optics_ray_trace` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Puzzles

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_puzzles_arithmetic_balance_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_arithmetic_equation_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_arithmetic_grid_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_logic_adjacency_completion_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_logic_grid_completion_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_spatial_assembly_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_spatial_cube_removal_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_spatial_fold_result_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_spatial_overlay_result_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_puzzles_topology_bead_equivalence_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Tables

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_tables_counting_value_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_ranking_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_readout_subset_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_relation_extremum_transfer_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_relation_row_compare_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_statistics_filtered_subset_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_statistics_filtered_subset_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_statistics_summary_label` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_statistics_summary_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tables_temporal_value` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Temporal

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_temporal_calendar_month_view` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_temporal_clock_compare` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_temporal_clock_readout` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_temporal_schedule_day_planner` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_temporal_timeline_milestones` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |

## Tile

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_tile_count_color_components` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_count_color_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_count_largest_component_size` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_path_reachable_target_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_path_shortest_path` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_pattern_match3_run_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_reachability_region_size` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_relation_min_distance` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_symmetry_violation_count` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
| `task_tile_transition_gravity_max_drop` | pending_current_probe | pending | n/a | n/a | n/a | pending | pending |
