# RLVR Evidence Reward Mapping

Proposed v1 mapping from each active TRACE task to the public RLVR evidence-reward contract it should use.

This file is intentionally task-facing rather than implementation-facing:
- the reward contract ids below are the public contracts we should store in instance metadata,
- multiple contracts may share internal matcher helpers later,
- every active task should appear exactly once in the task mapping below.

## Proposed evidence reward contracts

- `bbox_set_iou_v1`
  - Use for public evidence type `bbox_set`.
  - Matching rule: Hungarian assignment on predicted vs ground-truth boxes, then IoU-based score aggregation.

- `numeric_exact_v1`
  - Use for public evidence types `integer` and `integer_list`.
  - Matching rule: exact ordered numeric match after normalizing scalars to length-1 numeric sequences.

- `symbolic_set_exact_v1`
  - Use for public evidence types `label_set`, `edge_set`, and future `id_set`.
  - Matching rule: exact unordered set match after canonicalizing each item.
  - For `edge_set`, canonicalize each undirected edge as a sorted endpoint pair before comparison.

- `point_set_match_v1`
  - Use for public evidence types `graph_point`, `graph_point_set`, and `grid_point_set`.
  - Matching rule: exact unordered coordinate-set match.
  - Normalize singleton `graph_point` to a one-item point set before comparison.

- `sequence_exact_v1`
  - Use for public evidence types `label_sequence`, `label_path`, `grid_point_path`, and future `id_path`.
  - Matching rule: exact ordered sequence/path match after item-level normalization.
  - For symbolic items, compare normalized tokens exactly.
  - For coordinate items, compare normalized coordinate tuples exactly.

## Task mapping

### `bbox_set_iou_v1` — 57 tasks

**Diagrams**
- `task_diagrams_cycle_offset_stage_label`
- `task_diagrams_flow_next_step_label`
- `task_diagrams_hierarchy_ancestor_label`
- `task_diagrams_schematic_callout_target_label`
- `task_diagrams_set_diagram_region_sum_value`

**Documents**
- `task_documents_arithmetic_section_expression_value`
- `task_documents_layout_section_membership_label`
- `task_documents_readout_field_value`
- `task_documents_relation_section_extremum_value`
- `task_documents_selection_checkbox_count`

**Games**
- `task_games_bingo_completed_line_count`
- `task_games_cards_hand_count`
- `task_games_checkers_move_count`
- `task_games_connect_four_move_count`
- `task_games_dominoes_chain_count`
- `task_games_dots_and_boxes_capture_count`
- `task_games_go_group_liberty_count`
- `task_games_mancala_move_count`
- `task_games_nine_mens_morris_pieces_in_mill_count`
- `task_games_reversi_move_count`

**Geometry**
- `task_geometry_solid_view_count`

**Icons**
- `task_icons_counting_reference_match_count`
- `task_icons_counting_singleton_type`
- `task_icons_counting_size_relation`
- `task_icons_pattern_structured_violation`
- `task_icons_relation_between_two_anchors_count`
- `task_icons_relation_relative_position_type`
- `task_icons_sequence_missing_count`

**Physics**
- `task_physics_circuits_equivalent_resistance`
- `task_physics_mechanics_force_diagram`
- `task_physics_mechanics_lever_balance`
- `task_physics_mechanics_spring_extension`

**Puzzles**
- `task_puzzles_arithmetic_balance_value`
- `task_puzzles_arithmetic_equation_value`
- `task_puzzles_arithmetic_grid_value`
- `task_puzzles_logic_adjacency_completion_label`
- `task_puzzles_logic_grid_completion_label`
- `task_puzzles_spatial_assembly_label`
- `task_puzzles_spatial_cube_removal_count`
- `task_puzzles_spatial_fold_result_label`
- `task_puzzles_spatial_overlay_result_label`
- `task_puzzles_topology_bead_equivalence_count`

**Tables**
- `task_tables_counting_value_count`
- `task_tables_ranking_label`
- `task_tables_readout_subset_value`
- `task_tables_relation_extremum_transfer_value`
- `task_tables_relation_row_compare_label`
- `task_tables_statistics_filtered_subset_label`
- `task_tables_statistics_filtered_subset_value`
- `task_tables_statistics_summary_label`
- `task_tables_statistics_summary_value`
- `task_tables_temporal_value`

**Temporal**
- `task_temporal_calendar_month_view`
- `task_temporal_clock_compare`
- `task_temporal_clock_readout`
- `task_temporal_schedule_day_planner`
- `task_temporal_timeline_milestones`

### `numeric_exact_v1` — 5 tasks

**Charts**
- `task_charts_composition_subset_value`
- `task_charts_distribution_boxplot_label`
- `task_charts_distribution_density_label`
- `task_charts_readout_subset_value`
- `task_charts_statistics_summary_label`

### `symbolic_set_exact_v1` — 20 tasks

**Charts**
- `task_charts_counting_value_count`
- `task_charts_distribution_histogram_count`
- `task_charts_multiseries_pairwise_comparison_count`
- `task_charts_statistics_summary_value`
- `task_charts_trend_structure_value`

**Geometry**
- `task_geometry_analytical_2d_value`
- `task_geometry_analytical_3d_value`
- `task_geometry_counting_value`
- `task_geometry_similarity_count`

**Graph**
- `task_graph_comparison_largest_component_size`
- `task_graph_counting_articulation_point_count`
- `task_graph_counting_bridge_count`
- `task_graph_counting_degree_count`
- `task_graph_optimization_minimum_spanning_tree_weight`
- `task_graph_relation_reachable_count`
- `task_graph_relation_same_component_count`
- `task_graph_relation_unique_cycle_size`

**Icons**
- `task_icons_relation_mirror_symmetry`
- `task_icons_relation_occlusion_order`
- `task_icons_transformation_pair_count`

### `sequence_exact_v1` — 5 tasks

**Graph**
- `task_graph_order_topological_position`
- `task_graph_path_shortest_path_length`

**Tile**
- `task_tile_path_shortest_path`
- `task_tile_relation_min_distance`
- `task_tile_transition_gravity_max_drop`

### `point_set_match_v1` — 13 tasks

**Geometry**
- `task_geometry_comparison_value`
- `task_geometry_coordinate_relation`
- `task_geometry_graphing_count`
- `task_geometry_measurement_value`
- `task_geometry_transformation_match`

**Physics**
- `task_physics_optics_ray_trace`

**Tile**
- `task_tile_count_color_components`
- `task_tile_count_color_count`
- `task_tile_count_largest_component_size`
- `task_tile_path_reachable_target_count`
- `task_tile_pattern_match3_run_count`
- `task_tile_reachability_region_size`
- `task_tile_symmetry_violation_count`

## Coverage notes

- The task counts above sum to the current active-task total of `100`.
- No current active task uses public evidence types `id_set`, `id_path`, `point_set`, `point_path`, `grid_point_map`, or `measurement_ref_map`.
- `task_geometry_measurement_value` is the only active task that emits either `graph_point` or `graph_point_set` depending on the delegated legacy scene/query pair; both normalize to `point_set_match_v1`.
- `numeric_exact_v1` intentionally covers both scalar integer witnesses and ordered integer witness lists by normalizing scalars to length-1 numeric sequences.
- `sequence_exact_v1` intentionally covers both symbolic ordered witnesses and coordinate paths; keep `point_set_match_v1` separate because unordered coordinate sets are the most likely family to need geometric tolerance later.
- `task_geometry_analytical_2d_value` and `task_geometry_analytical_3d_value` now publish `label_set` evidence as canonical `ANNOTATION=VALUE` tokens, which lets them use `symbolic_set_exact_v1` while preserving the old annotation/value bindings in trace metadata.
- If a task’s public evidence type changes, update this file in the same patch that changes the task contract.
