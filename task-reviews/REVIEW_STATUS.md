# Task Review Status

Update this table after each review run.

| task_id | latest_run_id | status | notes |
|---|---|---|---|
| task_charts_composition_subset_value | task_charts_composition_subset_value | alright_for_now | distribution pass (stacked-bar / stacked-horizontal / pie / donut composition queries) |
| task_charts_counting_value_count | task_charts_counting_value_count | alright_for_now | distribution pass (above-threshold / below-threshold / inclusive-interval counting across supported chart types) |
| task_charts_distribution_boxplot_label | task_charts_distribution_boxplot_label | alright_for_now | distribution pass (highest-median / largest-IQR / smallest-IQR boxplot queries) |
| task_charts_distribution_density_label | task_charts_distribution_density_label | alright_for_now | distribution pass (highest-mode / lowest-mode / bimodal violin queries) |
| task_charts_distribution_histogram_count | task_charts_distribution_histogram_count | alright_for_now | distribution pass (modal-bin / interval-mass / cumulative-count histogram queries) |
| task_charts_multiseries_pairwise_comparison_count | task_charts_multiseries_pairwise_comparison_count | alright_for_now | distribution pass (grouped-bar / grouped-horizontal / multi-line / grouped-lollipop pairwise series comparisons) |
| task_charts_readout_subset_value | task_charts_readout_subset_value | alright_for_now | distribution pass (two-label sum / difference / extremum / mean readout queries) |
| task_charts_statistics_summary_label | task_charts_statistics_summary_label | alright_for_now | distribution pass (argmax / argmin / median-label queries) |
| task_charts_statistics_summary_value | task_charts_statistics_summary_value | alright_for_now | distribution pass (max / min / range / mean / median / sum / mode queries) |
| task_charts_trend_structure_value | task_charts_trend_structure_value | alright_for_now | distribution pass (peak / trough / increasing-streak / decreasing-streak queries) |
| task_diagrams_cycle_offset_stage_label | task_diagrams_cycle_offset_stage_label | alright_for_now | distribution pass (clockwise cycle before/after-k-step label queries) |
| task_diagrams_flow_next_step_label | task_diagrams_flow_next_step_label | alright_for_now | distribution pass (plain flowchart + swimlane direct-next and explicit-branch next-step queries) |
| task_diagrams_hierarchy_ancestor_label | task_diagrams_hierarchy_ancestor_label | alright_for_now | distribution pass (org-chart parent lookup + lowest-common-ancestor label queries) |
| task_diagrams_schematic_callout_target_label | task_diagrams_schematic_callout_target_label | alright_for_now | distribution pass (annotated schematic named-part + highlighted-part callout lookup) |
| task_diagrams_set_diagram_region_sum_value | task_diagrams_set_diagram_region_sum_value | alright_for_now | distribution pass (3-set overlap region-sum queries over named set / union / intersection semantics) |
| task_documents_arithmetic_section_expression_value | task_documents_arithmetic_section_expression_value | alright_for_now | distribution pass (section-local amount arithmetic over named document blocks with operand-value evidence only) |
| task_documents_layout_section_membership_label | task_documents_layout_section_membership_label | alright_for_now | distribution pass (field-label / field-value / label-value-pair section membership queries over structured document sections) |
| task_documents_readout_field_value | task_documents_readout_field_value | alright_for_now | distribution pass (field lookup across form / invoice / receipt documents with ordered label-value evidence) |
| task_documents_relation_section_extremum_value | task_documents_relation_section_extremum_value | alright_for_now | distribution pass (section-local earliest/latest date and largest/smallest amount queries) |
| task_documents_selection_checkbox_count | task_documents_selection_checkbox_count | alright_for_now | distribution pass (named checkbox-section checked/unchecked counts with checkbox-box evidence in reading order) |
| task_geometry_analytical_2d_value | task_geometry_analytical_2d_value | alright_for_now | distribution pass (scene/query consolidated wrapper) |
| task_geometry_analytical_3d_value | task_geometry_analytical_3d_value | alright_for_now | distribution pass (scene/query consolidated wrapper) |
| task_geometry_comparison_value | task_geometry_comparison_value | alright_for_now | distribution pass (scene/query consolidated wrapper) |
| task_geometry_counting_value | task_geometry_counting_value | alright_for_now | distribution pass (scene/query consolidated wrapper) |
| task_geometry_measurement_value | task_geometry_measurement_value | alright_for_now | distribution pass (scene/query consolidated wrapper) |
| task_geometry_coordinate_relation | task_geometry_coordinate_relation | alright_for_now | distribution pass (collinear + segment parallel/perpendicular counts + quadrant count + polygon interior-lattice count variants) |
| task_geometry_graphing_count | task_geometry_graphing_count | alright_for_now | distribution pass (quadratic/absolute-value/cubic/sinusoid/piecewise graphing x x-intercept/horizontal-line/turning-point/local-minima/local-maxima counts) |
| task_geometry_solid_view_count | task_geometry_solid_view_count | alright_for_now | distribution pass (top/front/right orthographic cube-view count variants) |
| task_geometry_similarity_count | task_geometry_similarity_count | alright_for_now | distribution pass (triangle/quadrilateral x congruent/similar with `target_count` support `0..5`) |
| task_geometry_transformation_match | task_geometry_transformation_match | alright_for_now | distribution pass (triangle/quadrilateral x translation/reflection/rotation) |
| task_icons_counting_reference_match_count | task_icons_counting_reference_match_count | alright_for_now | distribution pass (consolidated wrapper over type/color/orientation/attribute-binding legacy generators) |
| task_icons_counting_size_relation | task_icons_counting_size_relation | alright_for_now | distribution pass |
| task_icons_counting_singleton_type | task_icons_counting_singleton_type | alright_for_now | distribution pass |
| task_icons_relation_relative_position_type | task_icons_relation_relative_position_type | alright_for_now | distribution pass |
| task_icons_relation_occlusion_order | task_icons_relation_occlusion_order | alright_for_now | distribution pass |
| task_icons_relation_between_two_anchors_count | task_icons_relation_between_two_anchors_count | alright_for_now | distribution pass |
| task_icons_relation_mirror_symmetry | task_icons_relation_mirror_symmetry | needs_refresh | focused validation pass; 5-variant distribution refresh pending |
| task_icons_pattern_structured_violation | task_icons_pattern_structured_violation | alright_for_now | distribution pass (consolidated wrapper over row/grid legacy violation generators) |
| task_icons_sequence_missing_count | task_icons_sequence_missing_count | alright_for_now | distribution pass |
| task_icons_transformation_pair_count | task_icons_transformation_pair_count | alright_for_now | distribution pass |
| task_tile_count_color_components | task_tile_count_color_components | alright_for_now | distribution pass |
| task_tile_count_color_count | task_tile_count_color_count | alright_for_now | distribution pass |
| task_tile_count_largest_component_size | task_tile_count_largest_component_size | alright_for_now | distribution pass |
| task_tile_path_reachable_target_count | task_tile_path_reachable_target_count | alright_for_now | distribution pass |
| task_tile_path_shortest_path | task_tile_path_shortest_path | alright_for_now | distribution pass |
| task_tile_pattern_match3_run_count | task_tile_pattern_match3_run_count | alright_for_now | distribution pass (row + column variants with one canonical witness run per counted line) |
| task_tile_reachability_region_size | task_tile_reachability_region_size | alright_for_now | distribution pass |
| task_tile_relation_min_distance | task_tile_relation_min_distance | alright_for_now | distribution pass |
| task_tile_symmetry_violation_count | task_tile_symmetry_violation_count | alright_for_now | distribution pass (horizontal + vertical counted-side variants) |
| task_tile_transition_gravity_max_drop | task_tile_transition_gravity_max_drop | alright_for_now | distribution pass |
| task_graph_counting_degree_count | task_graph_counting_degree_count | alright_for_now | distribution pass (degree/in-degree/out-degree variants) |
| task_graph_counting_articulation_point_count | task_graph_counting_articulation_point_count | alright_for_now | distribution pass |
| task_graph_counting_bridge_count | task_graph_counting_bridge_count | alright_for_now | distribution pass |
| task_graph_comparison_largest_component_size | task_graph_comparison_largest_component_size | alright_for_now | distribution pass |
| task_graph_optimization_minimum_spanning_tree_weight | task_graph_optimization_minimum_spanning_tree_weight | alright_for_now | distribution pass |
| task_graph_order_topological_position | task_graph_order_topological_position | alright_for_now | distribution pass |
| task_graph_path_shortest_path_length | task_graph_path_shortest_path_length | alright_for_now | distribution pass |
| task_graph_relation_reachable_count | task_graph_relation_reachable_count | alright_for_now | distribution pass |
| task_graph_relation_same_component_count | task_graph_relation_same_component_count | alright_for_now | distribution pass |
| task_graph_relation_unique_cycle_size | task_graph_relation_unique_cycle_size | alright_for_now | distribution pass |
| task_temporal_clock_readout | task_temporal_clock_readout | alright_for_now | distribution pass |
| task_temporal_clock_compare | task_temporal_clock_compare | alright_for_now | distribution pass |
| task_temporal_calendar_month_view | task_temporal_calendar_month_view | alright_for_now | distribution pass |
| task_temporal_schedule_day_planner | task_temporal_schedule_day_planner | alright_for_now | distribution pass |
| task_temporal_timeline_milestones | task_temporal_timeline_milestones | alright_for_now | distribution pass |
| task_physics_mechanics_force_diagram | task_physics_mechanics_force_diagram | alright_for_now | distribution pass (axis-aligned free-body/textured-block force-diagram net-force + balancing-force variants) |
| task_physics_mechanics_lever_balance | task_physics_mechanics_lever_balance | alright_for_now | distribution pass (lever-balance left/right torque + missing-weight variants) |
| task_physics_mechanics_spring_extension | task_physics_mechanics_spring_extension | alright_for_now | distribution pass (identical-spring missing-weight / missing-extension / extension-difference variants) |
| task_physics_circuits_equivalent_resistance | task_physics_circuits_equivalent_resistance | alright_for_now | distribution pass (single-circuit total-resistance scenes plus paired missing-resistor scenes with equal resistance between labeled terminals A and B) |
| task_physics_optics_ray_trace | task_physics_optics_ray_trace | alright_for_now | distribution pass (hidden-path optics with graph-point evidence over bounce points / hit targets) |
| task_puzzles_arithmetic_balance_value | task_puzzles_arithmetic_balance_value | alright_for_now | distribution pass (stacked equality-panel arithmetic puzzle with one-box query evidence) |
| task_puzzles_arithmetic_equation_value | task_puzzles_arithmetic_equation_value | alright_for_now | distribution pass (one-row boxed arithmetic equation with result-unknown / operand-unknown variants) |
| task_puzzles_arithmetic_grid_value | task_puzzles_arithmetic_grid_value | alright_for_now | distribution pass (repeated-row arithmetic grid with sum / difference / product missing-cell variants) |
| task_puzzles_logic_adjacency_completion_label | task_puzzles_logic_adjacency_completion_label | alright_for_now | distribution pass (logic board with king-non-touch rule and winning option-panel evidence) |
| task_puzzles_logic_grid_completion_label | task_puzzles_logic_grid_completion_label | alright_for_now | distribution pass (logic board with row / column / row-and-column uniqueness option completion) |
| task_puzzles_spatial_assembly_label | task_puzzles_spatial_assembly_label | alright_for_now | distribution pass (piece-assembly silhouette selection with rotation allowed and no flipping) |
| task_puzzles_spatial_cube_removal_count | task_puzzles_spatial_cube_removal_count | alright_for_now | distribution pass (original-vs-remaining block comparison with ordered structure-pair evidence) |
| task_puzzles_spatial_fold_result_label | task_puzzles_spatial_fold_result_label | alright_for_now | distribution pass (paper-fold result selection with explicit dashed fold line and outside arrows) |
| task_puzzles_spatial_overlay_result_label | task_puzzles_spatial_overlay_result_label | alright_for_now | distribution pass (transparent-sheet overlay selection with fixed alignment and no rotation/flipping) |
| task_puzzles_topology_bead_equivalence_count | task_puzzles_topology_bead_equivalence_count | alright_for_now | distribution pass (bead-loop cyclic-equivalence counting with ordered valid-option evidence) |
| task_tables_statistics_summary_label | task_tables_statistics_summary_label | alright_for_now | distribution pass (column-extremum and row-total winner label variants with minimal decisive-region evidence) |
| task_tables_statistics_summary_value | task_tables_statistics_summary_value | alright_for_now | distribution pass (column / row / whole-table summary-value variants with region-level bbox evidence) |
| task_tables_statistics_filtered_subset_value | task_tables_statistics_filtered_subset_value | alright_for_now | distribution pass (filtered target-column sum / mean with ordered [filter cell, target cell] evidence pairs) |
| task_tables_statistics_filtered_subset_label | task_tables_statistics_filtered_subset_label | alright_for_now | distribution pass (filtered target-column argmax / argmin row-label variants with ordered witness pairs) |
| task_tables_counting_value_count | task_tables_counting_value_count | alright_for_now | distribution pass (single-column threshold/interval counts plus row-wise two-column comparison counts) |
| task_tables_readout_subset_value | task_tables_readout_subset_value | alright_for_now | distribution pass (single-cell lookup and ordered two-cell arithmetic readout variants) |
| task_tables_relation_row_compare_label | task_tables_relation_row_compare_label | alright_for_now | distribution pass (two-row same-column comparison with ordered compared-cell evidence) |
| task_tables_relation_extremum_transfer_value | task_tables_relation_extremum_transfer_value | alright_for_now | distribution pass (source-column extremum transfer to target-column value with ordered two-cell evidence) |
| task_tables_ranking_label | task_tables_ranking_label | alright_for_now | distribution pass (kth-highest / kth-lowest row-label ranking over one queried column) |
| task_tables_temporal_value | task_tables_temporal_value | alright_for_now | distribution pass (single-row chronological year-table readout / delta / interval aggregation variants) |
| task_games_dots_and_boxes_capture_count | task_games_dots_and_boxes_capture_count | alright_for_now | distribution pass (single-board dots-and-boxes scenes with highlighted forced-turn capture counting and box-level evidence over the captured chain) |
| task_games_bingo_completed_line_count | task_games_bingo_completed_line_count | alright_for_now | distribution pass (single-card `5 x 5` bingo boards with completed-row, completed-column, and completed-straight-line count variants) |
| task_games_cards_hand_count | task_games_cards_hand_count | alright_for_now | distribution pass (single-row/two-row visible card hands with same-suit, higher-rank, exact-pair, and longest-run count variants) |
| task_games_dominoes_chain_count | task_games_dominoes_chain_count | alright_for_now | distribution pass (top-chain plus loose-domino scenes with matching-end, higher-sum, target-sum, and double-count variants) |
| task_games_reversi_move_count | task_games_reversi_move_count | alright_for_now | distribution pass (compact/classic visible Reversi boards with legal-move, corner-move, and marked flip-count queries) |
| task_games_connect_four_move_count | task_games_connect_four_move_count | alright_for_now | distribution pass (midgame/crowded Connect Four boards with immediate-win and safe-move count variants) |
| task_games_checkers_move_count | task_games_checkers_move_count | alright_for_now | distribution pass (midgame/crowded Checkers boards with legal-move and capture-move count variants over unique landing squares) |
| task_games_mancala_move_count | task_games_mancala_move_count | alright_for_now | distribution pass (midgame/crowded visible Mancala boards with Blue-to-move extra-turn and capture count variants grounded on starting pits) |
| task_games_nine_mens_morris_pieces_in_mill_count | task_games_nine_mens_morris_pieces_in_mill_count | alright_for_now | distribution pass (single-board Morris scenes with white / black / all pieces-in-mill counting and piece-level evidence over the counted witnesses) |
