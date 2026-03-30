# TRACE TODO

## Now (P0)
1. No immediate P0 cleanup blockers; keep follow-up review findings flowing into docs/tests as new task families land.

## Next (P1)
1. Expand the charts domain beyond the current `statistics` + `counting` + `readout` + `multiseries` + `distribution` + `trend` + `composition` tasks and formalize the next chart reasoning families after `task_charts_statistics_summary_value`, `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, `task_charts_readout_subset_value`, `task_charts_multiseries_pairwise_comparison_count`, `task_charts_distribution_histogram_count`, `task_charts_distribution_boxplot_label`, `task_charts_distribution_density_label`, `task_charts_trend_structure_value`, and `task_charts_composition_subset_value`.
2. Extend the new icons domain beyond the current counting/transformation/relation/sequence set using the curated Prism asset pipeline (`comparison` remains the next natural family).
3. Expand the tables domain beyond `task_tables_statistics_summary_label`, `task_tables_statistics_summary_value`, `task_tables_statistics_filtered_subset_value`, `task_tables_statistics_filtered_subset_label`, `task_tables_counting_value_count`, `task_tables_readout_subset_value`, `task_tables_relation_row_compare_label`, `task_tables_relation_extremum_transfer_value`, `task_tables_ranking_label`, and `task_tables_temporal_value` with richer row/column relation tasks while keeping `bbox_set` as the fixed table evidence contract.
4. Expand the new puzzles domain beyond the current arithmetic + logic + spatial + first topology set (`task_puzzles_arithmetic_equation_value`, `task_puzzles_arithmetic_balance_value`, `task_puzzles_arithmetic_grid_value`, `task_puzzles_logic_grid_completion_label`, `task_puzzles_logic_adjacency_completion_label`, `task_puzzles_spatial_fold_result_label`, `task_puzzles_spatial_cube_removal_count`, `task_puzzles_spatial_assembly_label`, `task_puzzles_spatial_overlay_result_label`, and `task_puzzles_topology_bead_equivalence_count`) with additional spatial and topology families while keeping early evidence contracts local and visually obvious.
5. Expand the new maps domain beyond `task_maps_region_association_label` while reusing the same stylized region+legend scene contract first (`region_count`, `region_compare`, `region_lookup`) before moving into transit-map families.
6. Expand the v1 `rectangular_tiling` tile task suite beyond the current active set and keep future ports aligned to `docs/domains/TILE_TASK_SETUP.md`.
7. Add cross-domain `scene_variant` + role-binding spec in architecture/ABI docs.
8. Continue rolling out domain-owned task complexity policy: migrate remaining legacy ad hoc `complexity_score` formulas toward within-task normalized criterion values with domain/task-group weighting. The active chart and tile suites are now migrated; geometry and tables still need the same rollout.
9. Improve dataset QA diagnostics/report summaries.
10. Extend geometry comparison beyond angle/length/area/perimeter using the same label-answer + winner-gap contract.
11. Extend analytical geometry to additional objectives beyond the current analytical set (additional 3D objectives, richer conic/composite-region reasoning).

## Later (P2)
1. Add split-artifact generation with deterministic split policy metadata.
2. Add richer dataset inspection tooling around trace shards and build reports.
3. Keep future tile task groups aligned with `configs/domains/tile/base.yaml` shared defaults.
4. Expand geometry analytical task suite with multi-step composite-region and shaded-area reasoning.
5. Add geometry `estimate` task track for non-exact quantitative reasoning (for example count graph squares, count angles `< 90°`).

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
- `task_geometry_measurement_angle`
- `task_geometry_measurement_area`
- `task_geometry_measurement_perimeter`
- `task_geometry_measurement_length`
- `task_geometry_measurement_slope`
- `task_geometry_analytical_2d_area`
- `task_geometry_analytical_2d_length`
- `task_geometry_analytical_3d_volume`
- `task_geometry_analytical_3d_surface_area`
6. Task-review/sample-generation tooling with per-task artifacts and inspection workbooks.
7. Pre-finalize prompt validation checks (metadata/bundle/key/placeholder/cardinality).
8. First charts-domain tasks: `task_charts_statistics_summary_value`, `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, `task_charts_readout_subset_value`, `task_charts_multiseries_pairwise_comparison_count`, `task_charts_distribution_histogram_count`, `task_charts_distribution_boxplot_label`, `task_charts_distribution_density_label`, `task_charts_trend_structure_value`, `task_charts_composition_subset_value`.
9. First tables-domain tasks: `task_tables_statistics_summary_label`, `task_tables_statistics_summary_value`, `task_tables_statistics_filtered_subset_value`, `task_tables_statistics_filtered_subset_label`, `task_tables_counting_value_count`, `task_tables_readout_subset_value`, `task_tables_relation_row_compare_label`, `task_tables_relation_extremum_transfer_value`, `task_tables_ranking_label`, and `task_tables_temporal_value`.
10. First puzzles-domain arithmetic tasks: `task_puzzles_arithmetic_equation_value`, `task_puzzles_arithmetic_balance_value`, and `task_puzzles_arithmetic_grid_value`.
11. First puzzles-domain logic tasks: `task_puzzles_logic_grid_completion_label` and `task_puzzles_logic_adjacency_completion_label`.
12. First puzzles-domain spatial tasks: `task_puzzles_spatial_fold_result_label`, `task_puzzles_spatial_cube_removal_count`, `task_puzzles_spatial_assembly_label`, and `task_puzzles_spatial_overlay_result_label`.
13. First puzzles-domain topology task: `task_puzzles_topology_bead_equivalence_count`.
14. First maps-domain region task: `task_maps_region_association_label`.
