# TRACE TODO

## Now (P0)
1. No immediate P0 cleanup blockers; keep follow-up review findings flowing into docs/tests as new task families land.

## Next (P1)
1. Expand the new graph domain beyond the current degree/component/reachability/path/cycle/cut-vertex baseline with additional counting/comparison/topology tasks while keeping the v1 simple labeled node-link contract stable across undirected and explicit directed variants.
2. Extend the new temporal domain beyond `task_temporal_clock_readout`, `task_temporal_clock_compare`, `task_temporal_calendar_month_view`, `task_temporal_schedule_day_planner`, and `task_temporal_timeline_milestones` with additional time-structured visual artifacts while keeping each task tied to one stable visual scaffold and a local evidence contract.
3. Expand the charts domain beyond the current `statistics` + `counting` + `readout` + `multiseries` + `distribution` + `trend` + `composition` tasks and formalize the next chart reasoning families after `task_charts_statistics_summary_value`, `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, `task_charts_readout_subset_value`, `task_charts_multiseries_pairwise_comparison_count`, `task_charts_distribution_histogram_count`, `task_charts_distribution_boxplot_label`, `task_charts_distribution_density_label`, `task_charts_trend_structure_value`, and `task_charts_composition_subset_value`.
4. Extend the new icons domain beyond the current counting/transformation/relation/sequence/pattern set using the curated Prism asset pipeline (`comparison` plus richer pattern/transformation variants remain the next natural families).
5. Expand the tables domain beyond `task_tables_statistics_summary_label`, `task_tables_statistics_summary_value`, `task_tables_statistics_filtered_subset_value`, `task_tables_statistics_filtered_subset_label`, `task_tables_counting_value_count`, `task_tables_readout_subset_value`, `task_tables_relation_row_compare_label`, `task_tables_relation_extremum_transfer_value`, `task_tables_ranking_label`, and `task_tables_temporal_value` with richer row/column relation tasks while keeping `bbox_set` as the fixed table evidence contract.
6. Expand the v1 `rectangular_tiling` tile task suite beyond the current active set and keep future ports aligned to `docs/domains/TILE_TASK_SETUP.md`.
7. Add cross-domain `scene_variant` + role-binding spec in architecture/ABI docs.
8. Continue rolling out domain-owned task complexity policy: migrate remaining legacy ad hoc `complexity_score` formulas toward within-task normalized criterion values with domain/task-group weighting. The active icons, geometry, tile, charts, and graph suites are now migrated; tables and puzzles still need the same rollout.
9. Expand the new puzzles domain beyond the current arithmetic + logic + spatial + topology set (`task_puzzles_arithmetic_equation_value`, `task_puzzles_arithmetic_balance_value`, `task_puzzles_arithmetic_grid_value`, `task_puzzles_logic_grid_completion_label`, `task_puzzles_logic_adjacency_completion_label`, `task_puzzles_spatial_fold_result_label`, `task_puzzles_spatial_cube_removal_count`, `task_puzzles_spatial_assembly_label`, `task_puzzles_spatial_overlay_result_label`, and `task_puzzles_topology_bead_equivalence_count`) with additional spatial and topology families while keeping early evidence contracts local and visually obvious.
10. Expand the new documents domain beyond `task_documents_readout_field_value|task_documents_arithmetic_section_expression_value|task_documents_layout_section_membership_label|task_documents_relation_section_extremum_value|task_documents_selection_checkbox_count` with additional OCR-light structured-document families (`key_value` and later `line_items`) while keeping evidence grounded on the queried visible field units, ordered operand values, matching section headers, winning visible values, or counted checkbox squares rather than full-page boxes.
11. Expand the new maps domain beyond `task_maps_region_association_label|task_maps_region_count` while reusing the same stylized region+legend scene contract first (`region_compare`, `region_lookup`) before moving into transit-map families.
12. Expand the new diagrams domain beyond `task_diagrams_flow_next_step_label|task_diagrams_hierarchy_ancestor_label|task_diagrams_cycle_offset_stage_label|task_diagrams_set_diagram_region_sum_value` with additional flow and set-overlap tasks while reusing the same local-evidence schematic contract and keeping swimlane as a scene variant rather than a separate task group.
13. Improve dataset QA diagnostics/report summaries.
14. Extend geometry beyond the current value + transformation + similarity + coordinate + solid + graphing surface with additional visually distinct families (symmetry, solid/net reasoning, partition/region reasoning) rather than re-splitting value tasks back into one task id per predicate.
15. Extend consolidated analytical geometry beyond the current `task_geometry_analytical_2d_value` / `task_geometry_analytical_3d_value` scene/query surface (additional 3D objectives, richer conic/composite-region reasoning).

## Later (P2)
1. Add split-artifact generation with deterministic split policy metadata.
2. Add richer dataset inspection tooling around trace shards and build reports.
3. Keep future tile task groups aligned with `configs/domains/tile/base.yaml` shared defaults.
4. Expand consolidated geometry analytical coverage with multi-step composite-region and shaded-area reasoning.
5. Add geometry `estimate` task track for non-exact quantitative reasoning (for example count graph squares, count angles `< 90°`) if it lands with a meaningfully different visual/evidence contract from the current five-task geometry surface.

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
- Dataset ABI stores exact evidence values; tolerance policy remains training/reward-stage configurable.
2. Polygon measurement variants not in current scope:
- polygon diameter
- polygon min-side / max-side

## Done (high level)
1. Core deterministic build/ABI/trace pipeline and strict-repro framework.
2. Validation/reporting baseline and error-code catalog.
3. External prompt-bundle system and migration of active tasks.
4. Domain/task-group config loader and deterministic visual-variation infrastructure.
5. Initial grounded tasks:
- `task_tile_path_shortest_path`
- `task_tile_count_color_count`
- `task_tile_count_color_components`
- `task_tile_reachability_region_size`
- `task_tile_relation_min_distance`
- `task_geometry_measurement_value`
- `task_geometry_comparison_value`
- `task_geometry_counting_value`
- `task_geometry_analytical_2d_value`
- `task_geometry_analytical_3d_value`
6. Task-review/sample-generation tooling with per-task artifacts and inspection workbooks.
7. Pre-finalize prompt validation checks (metadata/bundle/key/placeholder/cardinality).
8. First charts-domain tasks: `task_charts_statistics_summary_value`, `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, `task_charts_readout_subset_value`, `task_charts_multiseries_pairwise_comparison_count`, `task_charts_distribution_histogram_count`, `task_charts_distribution_boxplot_label`, `task_charts_distribution_density_label`, `task_charts_trend_structure_value`, `task_charts_composition_subset_value`.
9. First tables-domain tasks: `task_tables_statistics_summary_label`, `task_tables_statistics_summary_value`, `task_tables_statistics_filtered_subset_value`, `task_tables_counting_value_count`, `task_tables_readout_subset_value`, `task_tables_relation_row_compare_label`, `task_tables_relation_extremum_transfer_value`, `task_tables_ranking_label`, and `task_tables_temporal_value`.
9. First tables-domain tasks: `task_tables_statistics_summary_label`, `task_tables_statistics_summary_value`, `task_tables_statistics_filtered_subset_value`, `task_tables_statistics_filtered_subset_label`, `task_tables_counting_value_count`, `task_tables_readout_subset_value`, `task_tables_relation_row_compare_label`, `task_tables_relation_extremum_transfer_value`, `task_tables_ranking_label`, and `task_tables_temporal_value`.
10. First puzzles-domain arithmetic tasks: `task_puzzles_arithmetic_equation_value`, `task_puzzles_arithmetic_balance_value`, and `task_puzzles_arithmetic_grid_value`.
11. First puzzles-domain logic tasks: `task_puzzles_logic_grid_completion_label` and `task_puzzles_logic_adjacency_completion_label`.
12. First puzzles-domain spatial tasks: `task_puzzles_spatial_fold_result_label`, `task_puzzles_spatial_cube_removal_count`, `task_puzzles_spatial_assembly_label`, and `task_puzzles_spatial_overlay_result_label`.
13. First puzzles-domain topology task: `task_puzzles_topology_bead_equivalence_count`.
14. First maps-domain region tasks: `task_maps_region_association_label` and `task_maps_region_count`.
15. First documents-domain readout task: `task_documents_readout_field_value`.
16. First documents-domain section-local arithmetic task: `task_documents_arithmetic_section_expression_value`.
17. First documents-domain layout-localization task: `task_documents_layout_section_membership_label`.
18. First documents-domain section-local relation task: `task_documents_relation_section_extremum_value`.
19. First documents-domain section-local selection/count task: `task_documents_selection_checkbox_count`.
20. First diagrams-domain flow task: `task_diagrams_flow_next_step_label`.
21. First diagrams-domain hierarchy task: `task_diagrams_hierarchy_ancestor_label`.
