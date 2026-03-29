# TRACE Prompt System

Prompt text is externalized and deterministic.

## 1) Core contract
1. Task modules must not hardcode user-facing prompt strings.
2. Bundles live under `prompts/<domain>/<task_group>/<bundle_id>.json`.
3. Composition layers:
   - task family,
   - task,
   - optional task variant,
   - output mode (`answer_only`, `answer_and_evidence`).
4. Selection is deterministic from seed namespaces.
5. Each required template list must contain exactly 5 high-quality variants.
6. All active tasks must provide explicit JSON-format instructions in both output modes:
   - `answer_only` uses `{"answer": ...}`
   - `answer_and_evidence` uses `{"evidence": ..., "answer": ...}`
7. Prefer slot-based composition for reusable format rules (for example shared `json_output_contract*` in domain/task-group config, with task-level `evidence_hint`/`answer_hint`/example overrides).
8. For mixed-shape tasks, keep one bundle and switch shape-specific wording via slots (`object_description_*`, `question_text_*`, evidence/answer hint families).
9. When a prompt asks about a named color, include the canonical hex code in the prompt-facing color label using the format `<color_name> [#RRGGBB]`.
10. For reference-panel tasks, keep the task-family layer responsible for establishing the panel layout so task-layer wording can focus on the matching rule itself.

## 2) Bundle schema (v1)
Required fields:
1. `bundle_id`
2. `schema_version`
3. `task_family_templates`
4. `task_templates`
5. `answer_or_evidence_templates`
6. `required_slots_by_key`
7. Optional: `task_variant_templates`

## 3) Metadata requirements
Trace `query_spec.prompt_variant` should include:
1. bundle/key identifiers (`task_family_key`, `task_key`, optional `task_variant_key`),
2. selected variant indices,
3. variant counts,
4. slot values for declared required slots,
5. output-mode key/index when mode templates exist.

Train records should store:
1. active `prompt`,
2. all rendered mode variants in `prompt_variants`.

## 4) Shared implementation
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and composition.
5. `trace/tasks/shared/prompt_variants.py` — task-level dual-mode orchestration.

## 4.1 Prompt-quality policy
1. Prefer 5 strong variants over larger padded lists.
2. Keep stems natural and image-focused; avoid awkward scaffolding such as “single/exactly one object” unless the distinction is semantically necessary.
3. Keep output-mode variants concise and structurally consistent so format requirements stay easy to parse.

## 5) Active bundles/tasks
Active bundles:
1. Geometry:
   - `prompts/geometry/comparison/geometry_comparison_v1.json`
   - `prompts/geometry/counting/geometry_counting_v1.json`
   - `prompts/geometry/measurement/geometry_angle_measure_v1.json`
   - `prompts/geometry/measurement/geometry_measurement_v1.json`
   - `prompts/geometry/analytical_2d/geometry_analytical_area_v1.json`
   - `prompts/geometry/analytical_2d/geometry_analytical_composite_area_v1.json`
   - `prompts/geometry/analytical_2d/geometry_analytical_length_v1.json`
   - `prompts/geometry/analytical_2d/geometry_analytical_perimeter_v1.json`
   - `prompts/geometry/analytical_3d/geometry_analytical_volume_v1.json`
   - `prompts/geometry/analytical_3d/geometry_analytical_surface_area_v1.json`
2. Icons:
   - `prompts/icons/counting/icons_counting_v1.json`
   - `prompts/icons/pattern/icons_pattern_v1.json`
   - `prompts/icons/relation/icons_relation_v1.json`
   - `prompts/icons/sequence/icons_sequence_v1.json`
   - `prompts/icons/transformation/icons_transformation_v1.json`
3. Graph:
   - `prompts/graph/counting/graph_counting_v1.json`
   - `prompts/graph/comparison/graph_comparison_v1.json`
   - `prompts/graph/order/graph_order_v1.json`
   - `prompts/graph/optimization/graph_optimization_v1.json`
   - `prompts/graph/path/graph_path_v1.json`
   - `prompts/graph/relation/graph_relation_v1.json`
4. Tile:
   - `prompts/tile/count/tile_count_v1.json`
   - `prompts/tile/path/tile_path_v1.json`
   - `prompts/tile/pattern/tile_pattern_v1.json`
   - `prompts/tile/reachability/tile_reachability_v1.json`
   - `prompts/tile/relation/tile_relation_v1.json`
   - `prompts/tile/symmetry/tile_symmetry_v1.json`
   - `prompts/tile/transition/tile_transition_v1.json`
5. Charts:
   - `prompts/charts/statistics/charts_statistics_v1.json`
   - `prompts/charts/counting/charts_counting_v1.json`
   - `prompts/charts/readout/charts_readout_v1.json`
   - `prompts/charts/multiseries/charts_multiseries_v1.json`
   - `prompts/charts/distribution/charts_distribution_v1.json`
   - `prompts/charts/trend/charts_trend_v1.json`
   - `prompts/charts/composition/charts_composition_v1.json`
6. Tables:
   - `prompts/tables/statistics/tables_statistics_v1.json`
   - `prompts/tables/counting/tables_counting_v1.json`
   - `prompts/tables/readout/tables_readout_v1.json`
   - `prompts/tables/relation/tables_relation_v1.json`
   - `prompts/tables/ranking/tables_ranking_v1.json`
   - `prompts/tables/temporal/tables_temporal_v1.json`
7. Temporal:
   - `prompts/temporal/clock/temporal_clock_v1.json`
8. Puzzles:
   - `prompts/puzzles/arithmetic/puzzles_arithmetic_v1.json`

Active task-to-bundle mapping:
1. Geometry comparison tasks (`task_geometry_comparison_angle|area|length|perimeter`) -> `geometry_comparison_v1`
2. Geometry counting tasks (`task_geometry_counting_angle|triangle|quadrilateral|shape_type|convexity`) -> `geometry_counting_v1`
3. Geometry measurement tasks:
   - `task_geometry_measurement_angle` -> `geometry_angle_measure_v1`
   - `task_geometry_measurement_area|perimeter|length|slope` -> `geometry_measurement_v1`
4. Geometry analytical 2D tasks:
   - `task_geometry_analytical_2d_area` -> `geometry_analytical_area_v1`
   - `task_geometry_analytical_2d_composite_area` -> `geometry_analytical_composite_area_v1`
   - `task_geometry_analytical_2d_length` -> `geometry_analytical_length_v1`
   - `task_geometry_analytical_2d_perimeter` -> `geometry_analytical_perimeter_v1`
5. Geometry analytical 3D tasks:
   - `task_geometry_analytical_3d_volume` -> `geometry_analytical_volume_v1`
   - `task_geometry_analytical_3d_surface_area` -> `geometry_analytical_surface_area_v1`
6. Icons:
   - `task_icons_counting_type|orientation|color|attribute_binding|size_relation|singleton_type` -> `icons_counting_v1`
   - `task_icons_pattern_grid_rotation_violation|task_icons_pattern_grid_size_violation` -> `icons_pattern_v1`
   - `task_icons_relation_relative_position_type|between_two_anchors_count|mirror_symmetry|occlusion_order` -> `icons_relation_v1`
   - `task_icons_sequence_missing_count|rotation_violation` -> `icons_sequence_v1`
   - `task_icons_transformation_pair_count` -> `icons_transformation_v1`
7. Graph:
   - `task_graph_counting_degree_count|articulation_point_count|bridge_count` -> `graph_counting_v1`
   - `task_graph_comparison_largest_component_size` -> `graph_comparison_v1`
   - `task_graph_order_topological_position` -> `graph_order_v1`
   - `task_graph_optimization_minimum_spanning_tree_weight` -> `graph_optimization_v1`
   - `task_graph_path_shortest_path_length` -> `graph_path_v1`
   - `task_graph_relation_same_component_count|reachable_count|unique_cycle_size` -> `graph_relation_v1`
8. Temporal:
   - `task_temporal_clock_readout|task_temporal_clock_compare` -> `temporal_clock_v1`
9. Tile:
   - `task_tile_count_color_count|color_components|largest_component_size` -> `tile_count_v1`
   - `task_tile_path_shortest_path|reachable_target_count` -> `tile_path_v1`
   - `task_tile_pattern_match3_run_count` -> `tile_pattern_v1`
   - `task_tile_reachability_region_size` -> `tile_reachability_v1`
   - `task_tile_relation_min_distance` -> `tile_relation_v1`
   - `task_tile_symmetry_violation_count` -> `tile_symmetry_v1`
   - `task_tile_transition_gravity_max_drop` -> `tile_transition_v1`
10. Charts:
   - `task_charts_statistics_summary_value|summary_label` -> `charts_statistics_v1`
   - `task_charts_counting_value_count` -> `charts_counting_v1`
   - `task_charts_readout_subset_value` -> `charts_readout_v1`
   - `task_charts_multiseries_pairwise_comparison_count` -> `charts_multiseries_v1`
   - `task_charts_distribution_histogram_count|boxplot_label|density_label` -> `charts_distribution_v1`
   - `task_charts_trend_structure_value` -> `charts_trend_v1`
   - `task_charts_composition_subset_value` -> `charts_composition_v1`
11. Tables:
   - `task_tables_statistics_summary_label|summary_value|filtered_subset_value|filtered_subset_label` -> `tables_statistics_v1`
   - `task_tables_counting_value_count` -> `tables_counting_v1`
   - `task_tables_readout_subset_value` -> `tables_readout_v1`
   - `task_tables_relation_row_compare_label|extremum_transfer_value` -> `tables_relation_v1`
   - `task_tables_ranking_label` -> `tables_ranking_v1`
   - `task_tables_temporal_value` -> `tables_temporal_v1`
12. Puzzles:
   - `task_puzzles_arithmetic_equation_value|task_puzzles_arithmetic_balance_value` -> `puzzles_arithmetic_v1`
