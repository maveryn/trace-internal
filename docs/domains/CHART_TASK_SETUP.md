# Chart Task Setup

## Purpose
Charts is the public domain for synthetic data displays, including chart renderers and the `table` scene.

The public taxonomy is `domain -> scene_id -> task_id`. Public `task_id` is the default sampling unit. Query mirrors and semantic branches are recorded as `query_id` and trace params, not public sampling units.

## Active Scenes
- `area`: 3 active task(s)
- `boxplot`: 3 active task(s)
- `candlestick`: 2 active task(s)
- `combo_mark`: 5 active task(s)
- `part_whole`: 4 active task(s)
- `dashboard`: 5 active task(s)
- `table`: 4 active task(s)
- `dumbbell`: 2 active task(s)
- `error_interval`: 2 active task(s)
- `heatmap`: 3 active task(s)
- `histogram`: 2 active task(s)
- `matrix`: 2 active task(s)
- `marker_map`: 2 active task(s)
- `region_map`: 5 active task(s)
- `multiseries`: 3 active task(s)
- `scatter_readout`: 2 active task(s)
- `parallel_coords`: 3 active task(s)
- `pictogram`: 3 active task(s)
- `radar`: 3 active task(s)
- `radial_progress`: 1 active task(s)
- `radial_sankey`: 2 active task(s)
- `sankey`: 2 active task(s)
- `scatter_cluster`: 2 active task(s)
- `curve_panels`: 5 active task(s)
- `single_series`: 8 active task(s)
- `size_encoding`: 3 active task(s)
- `small_multiple`: 2 active task(s)
- `sunburst`: 3 active task(s)
- `bar_3d`: 3 active task(s)
- `surface_3d`: 4 active task(s)
- `treemap`: 2 active task(s)
- `violin`: 2 active task(s)
- `waterfall`: 3 active task(s)

## Active Tasks

| Scene id | Task id | Query id |
|---|---|---|
| `area` | `task_charts__area__interval_area_value` | `interval_area_value` |
| `area` | `task_charts__area__stacked_band_interval_sum_value` | `stacked_band_interval_sum_value` |
| `area` | `task_charts__area__stacked_band_dominance_label` | `stacked_dominance_label` |
| `boxplot` | `task_charts__boxplot__median_rank_difference_value` | sampled from `median_top_second_difference_value`, `median_top_third_difference_value`, `median_top_bottom_difference_value` |
| `boxplot` | `task_charts__boxplot__paired_median_shift_label` | sampled from `paired_median_greatest_increase_label`, `paired_median_greatest_decrease_label`, `paired_median_greatest_absolute_change_label` |
| `boxplot` | `task_charts__boxplot__summary_statistic_label` | sampled from `median_reference_label`, `iqr_extremum_label` |
| `candlestick` | `task_charts__candlestick__counterfactual_close_value` | `close_after_body_change_value` |
| `candlestick` | `task_charts__candlestick__range_extremum_label` | sampled from `wick_range_extremum_label`, `body_range_extremum_label` |
| `combo_mark` | `task_charts__combo_mark__conditioned_extremum_label` | sampled from `max_line_where_primary_above_threshold`, `min_line_where_primary_above_threshold`, `max_primary_where_line_below_threshold`, `min_primary_where_line_below_threshold` |
| `combo_mark` | `task_charts__combo_mark__cross_mark_difference_value` | sampled from `primary_minus_line_at_label`, `line_minus_primary_at_label` |
| `combo_mark` | `task_charts__combo_mark__dual_condition_count` | sampled from `primary_above_and_line_above`, `primary_above_and_line_below`, `primary_below_and_line_above`, `primary_between_and_line_above` |
| `combo_mark` | `task_charts__combo_mark__gap_extremum_label` | sampled from `largest_absolute_gap_label`, `smallest_nonzero_absolute_gap_label`, `largest_primary_over_line_gap_label`, `largest_line_over_primary_gap_label` |
| `combo_mark` | `task_charts__combo_mark__interval_change_comparison_value` | sampled from `line_change_minus_primary_change`, `primary_change_minus_line_change`, `absolute_change_gap`, `larger_change_minus_smaller_change` |
| `region_map` | `task_charts__region_map__adjacent_condition_count` | sampled from `adjacent_same_category_count`, `adjacent_category_count`, `adjacent_numeric_threshold_count` |
| `region_map` | `task_charts__region_map__border_neighbor_count` | `border_neighbor_count` |
| `region_map` | `task_charts__region_map__continent_filtered_count` | sampled from `continent_region_count`, `continent_category_region_count`, `continent_threshold_region_count` |
| `region_map` | `task_charts__region_map__region_category_count` | `categorical_region_count` |
| `region_map` | `task_charts__region_map__region_value_count` | sampled from `numeric_threshold_region_count`, `numeric_interval_region_count` |
| `marker_map` | `task_charts__marker_map__marker_region_extremum_label` | `marker_region_extremum_label` |
| `marker_map` | `task_charts__marker_map__marker_region_threshold_count` | `marker_region_threshold_count` |
| `part_whole` | `task_charts__part_whole__order_share_sum_value` | sampled from `contiguous_chart_order_sum`, `positional_segment_share_sum` |
| `part_whole` | `task_charts__part_whole__order_count_conversion_value` | `chart_order_share_to_count` |
| `part_whole` | `task_charts__part_whole__order_sector_angle_value` | `sector_share_to_angle` |
| `part_whole` | `task_charts__part_whole__adjacent_transfer_gap_value` | `chart_order_adjacent_transfer_gap` |
| `dashboard` | `task_charts__dashboard__dual_condition_count` | `dual_condition_count` |
| `dashboard` | `task_charts__dashboard__dual_source_target_sum_value` | `dual_source_target_sum_value` |
| `dashboard` | `task_charts__dashboard__panel_gap_extremum_category_label` | `panel_gap_extremum_category_label` |
| `dashboard` | `task_charts__dashboard__source_rank_difference_value` | `source_rank_difference_value` |
| `dashboard` | `task_charts__dashboard__source_rank_target_value` | `source_rank_target_value` |
| `table` | `task_charts__table__value_predicate_count` | sampled from `threshold_count`, `in_interval`, `categorical_value_count` |
| `table` | `task_charts__table__column_rank_label` | `kth_rank_in_column` |
| `table` | `task_charts__table__column_summary_value` | sampled from `column_sum`, `column_mean`, `column_median`, `filtered_column_mean` |
| `table` | `task_charts__table__temporal_row_interval_difference_value` | sampled from `absolute_difference_between_rows_over_year_interval`, `sum_absolute_differences_between_rows_over_year_interval` |
| `dumbbell` | `task_charts__dumbbell__gap_rank_row_label` | `gap_rank_row_label` |
| `dumbbell` | `task_charts__dumbbell__pair_relation_count` | sampled from `side_winner_count`, `absolute_gap_threshold_count` |
| `error_interval` | `task_charts__error_interval__reference_relation_count` | sampled from `contains_reference_count`, `entirely_above_reference_count`, `entirely_below_reference_count` |
| `error_interval` | `task_charts__error_interval__interval_width_rank_label` | sampled from `widest_interval_label`, `narrowest_interval_label`, `second_widest_interval_label`, `second_narrowest_interval_label` |
| `heatmap` | `task_charts__heatmap__axis_cell_extremum_label` | `axis_cell_extremum_label` |
| `heatmap` | `task_charts__heatmap__axis_condition_extremum_label` | `axis_condition_extremum_label` |
| `heatmap` | `task_charts__heatmap__condition_run_extremum_label` | `condition_run_extremum_label` |
| `histogram` | `task_charts__histogram__cumulative_rank_bin_label` | `rank_item_bin_label` |
| `histogram` | `task_charts__histogram__interval_value` | sampled from `interval_mass`, `bin_count_between_values` |
| `matrix` | `task_charts__matrix__axis_extremum_label` | sampled from `axis_extremum_label`, `off_diagonal_confusion_label` |
| `matrix` | `task_charts__matrix__threshold_cell_count` | `threshold_cell_count` |
| `multiseries` | `task_charts__multiseries__category_total_extremum_label` | `category_total_extremum_label` |
| `multiseries` | `task_charts__multiseries__ranked_metric_extremum_label` | sampled from `ranked_change_extremum`, `ranked_ratio_extremum` |
| `multiseries` | `task_charts__multiseries__series_comparison_count` | `series_comparison_count` |
| `parallel_coords` | `task_charts__parallel_coords__axis_condition_count` | sampled from `above_on_both_axes`, `below_on_both_axes`, `above_on_one_below_on_other` |
| `parallel_coords` | `task_charts__parallel_coords__axis_delta_extremum_label` | sampled from `largest_increase_between_axes`, `largest_decrease_between_axes`, `largest_absolute_change_between_axes` |
| `parallel_coords` | `task_charts__parallel_coords__crossing_count` | sampled from `all_crossings_between_adjacent_axes`, `crossings_involving_profile_between_axes` |
| `pictogram` | `task_charts__pictogram__category_total_value` | `category_total_value` |
| `pictogram` | `task_charts__pictogram__group_difference_value` | `group_difference_value` |
| `pictogram` | `task_charts__pictogram__threshold_count` | `threshold_count` |
| `radial_progress` | `task_charts__radial_progress__condition_count` | sampled from `at_least_threshold_count`, `below_threshold_count`, `within_range_count`, `remaining_at_least_threshold_count` |
| `scatter_readout` | `task_charts__scatter_readout__series_x_extremum_label` | sampled from `series_highest_x_label`, `series_lowest_x_label` |
| `scatter_readout` | `task_charts__scatter_readout__series_point_lookup_value` | sampled from `series_pair_value_gap_at_x`, `series_y_anchor_other_series_value` |
| `radar` | `task_charts__radar__profile_advantage_count` | `profile_advantage_count` |
| `radar` | `task_charts__radar__threshold_panel_count` | sampled from `highlighted_metric_threshold_panel_count`, `matching_condition_panel_count` |
| `radar` | `task_charts__radar__threshold_metric_count_for_panel` | `threshold_metric_count_for_panel` |
| `radial_sankey` | `task_charts__radial_sankey__dominant_endpoint_label` | sampled from `largest_target_for_source`, `largest_source_for_target`, `second_largest_target_for_source` |
| `radial_sankey` | `task_charts__radial_sankey__transfer_total_value` | sampled from `source_to_targets_total`, `sources_to_target_total` |
| `sankey` | `task_charts__sankey__node_side_total_value` | sampled from `source_outgoing_total_flow`, `target_incoming_total_flow` |
| `sankey` | `task_charts__sankey__path_value` | sampled from `source_to_target_total_flow`, `path_bottleneck_value`, `path_flow_difference` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_feature_extremum_label` | sampled from `cluster_separation_extremum_label`, `cluster_spread_extremum_label` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_trend_direction_label` | `cluster_trend_direction_label` |
| `curve_panels` | `task_charts__curve_panels__cross_panel_delta_extremum_label` | `cross_panel_delta_extremum_label` |
| `curve_panels` | `task_charts__curve_panels__curve_at_x_extremum_label` | `curve_at_x_extremum_label` |
| `curve_panels` | `task_charts__curve_panels__curve_intersection_count` | `curve_intersection_count` |
| `curve_panels` | `task_charts__curve_panels__earliest_maximum_panel_label` | `earliest_maximum_panel_label` |
| `curve_panels` | `task_charts__curve_panels__threshold_series_count` | `threshold_series_count` |
| `single_series` | `task_charts__single_series__value_predicate_count` | sampled from `threshold_count`, `in_interval` |
| `single_series` | `task_charts__single_series__counterfactual_value` | sampled from `remaining_mean_after_removal`, `target_share_after_removal`, `baseline_from_aggregate_percent_change` |
| `single_series` | `task_charts__single_series__order_statistic_value` | `order_statistic_value` |
| `single_series` | `task_charts__single_series__order_statistic_label` | `order_statistic_label` |
| `single_series` | `task_charts__single_series__interval_change_value` | sampled from `endpoint_change_value`, `interval_rate_value` |
| `single_series` | `task_charts__single_series__monotone_streak_length` | `longest_monotone_streak` |
| `single_series` | `task_charts__single_series__threshold_crossing_label` | `threshold_crossing` |
| `single_series` | `task_charts__single_series__turning_point_count` | `turning_point_count` |
| `size_encoding` | `task_charts__size_encoding__category_total_extremum_label` | `category_total_extremum_label` |
| `size_encoding` | `task_charts__size_encoding__filtered_item_extremum_label` | `filtered_item_extremum_label` |
| `size_encoding` | `task_charts__size_encoding__reference_size_neighbor_label` | `reference_size_neighbor_label` |
| `small_multiple` | `task_charts__small_multiple__aggregate_value` | sampled from `top_k_by_segment_then_sum_other_segment_count`, `conditioned_panel_sum_from_percent` |
| `small_multiple` | `task_charts__small_multiple__difference_value` | sampled from `average_top_k_minus_average_bottom_k`, `composition_shift_l1_distance` |
| `sunburst` | `task_charts__sunburst__conditional_leaf_count` | sampled from `leaf_threshold_count_under_parent`, `leaf_range_count_under_parent` |
| `sunburst` | `task_charts__sunburst__parent_total_extremum_label` | sampled from `highest_parent_total_label`, `lowest_parent_total_label` |
| `sunburst` | `task_charts__sunburst__parent_total_value` | `parent_total_from_leaves_value` |
| `treemap_part_whole` | `task_charts__treemap__group_total_value` | `treemap_group_total_value` |
| `treemap_part_whole` | `task_charts__treemap__repeated_leaf_aggregate_value` | sampled from `treemap_repeated_leaf_sum_value`, `treemap_repeated_leaf_average_value` |
| `bar_3d` | `task_charts__bar_3d__axis_gap_value` | sampled from `series_total_gap_value`, `category_total_gap_value`, `category_extremum_gap_value` |
| `bar_3d` | `task_charts__bar_3d__axis_total_value` | sampled from `series_total_value`, `category_total_value`, `series_interval_total_value` |
| `bar_3d` | `task_charts__bar_3d__condition_count` | sampled from `series_threshold_count`, `category_threshold_count`, `series_comparison_count` |
| `surface_3d` | `task_charts__surface_3d__panel_variation_label` | `panel_variation_label` |
| `surface_3d` | `task_charts__surface_3d__reference_nearest_label` | `reference_nearest_label` |
| `surface_3d` | `task_charts__surface_3d__series_trend_label` | `series_trend_label` |
| `surface_3d` | `task_charts__surface_3d__surface_extremum_label` | `surface_extremum_label` |
| `violin` | `task_charts__violin__feature_extremum_label` | sampled from `highest_mode`, `lowest_mode`, `widest_support`, `narrowest_support` |
| `violin` | `task_charts__violin__shape_feature_label` | `bimodal_label` |
| `waterfall` | `task_charts__waterfall__counterfactual_final_value` | sampled from `remove_step_final_total`, `reverse_step_final_total` |
| `waterfall` | `task_charts__waterfall__running_total_value` | `running_total_after_step` |
| `waterfall` | `task_charts__waterfall__threshold_crossing_label` | sampled from `first_total_at_least_threshold`, `first_total_at_most_threshold` |

## Refactor Rules
1. The meaningful semantic branch is kept in `query_id` and trace params.
2. `query_variant` is an internal replay selector, not a public sampling unit.
3. Chart type, palette, background, row/column axis, largest/smallest, highest/lowest, clockwise/counterclockwise, and other mirror/rendering choices stay internal query or render params.
4. Shared broad generators may remain internal implementation details, but only active public task IDs are registered.
5. Fresh task-review workbooks and solve-rate probes are required for current public task IDs.

## Scene Render Notes
1. `region_map` covers synthetic region maps and bundled Natural Earth-derived geographic maps under `assets/charts/maps/`. Mixed map tasks sample synthetic maps and geographic maps; geographic maps sample world countries, contiguous USA states, EU countries, and China provinces. Filtered-continent and border-neighbor tasks are restricted to the world-country asset. Filtered-continent targets `Africa`, `Asia`, `Europe`, `North America`, or `South America`; border-neighbor uses exact shared boundary segments with configured shared-border length and neighbor-area thresholds; adjacent-condition tasks count colored neighbors touching a highlighted reference region. `marker_map` reuses the same map assets and synthetic map grammar but encodes values with marker bubbles over labeled regions; evidence is always marker-bubble `bbox_set` evidence. These assets supply geometry and geography metadata only; task values, category labels, assignments, and counted regions are synthetic and verified from TRACE metadata. Runtime generation must not download map geometry. The renderer preserves each geographic asset's longitude/latitude aspect ratio, samples map styles and legend placement, and records selected style metadata under `render_spec.map_render_style`.
2. Chart post-render noise follows the domain policy in `configs/domains/charts/base.yaml`: `apply_prob=0.5` with coordinate-preserving `blur`, `downsample`, `jpeg`, and additive/noise-like edits. The `table` scene uses the chart table group configs under `configs/domains/charts/table_*.yaml`. Scene/task groups should not override this without a documented exception and a trace-level audit.
3. Prompt bundles should use the normal scene/task/query layering. The scene sentence describes what the image shows, task/query text asks for the reasoning target, and answer+evidence prompts must include a named `Evidence format:` section.
4. `violin` samples non-semantic violin styling: optional/subtle mode markers, fill style, width/smoothing scale, and single vs per-violin muted palettes. These choices are recorded in `render_spec.violin_style` and must not change the symbolic supports, mode values, or answer/evidence contract.
5. `sunburst` is a not-to-scale concentric hierarchy display. Ring geometry encodes parent/subgroup/leaf structure only; printed outer leaf values are the numeric source of truth, and the render spec records `not_to_scale=true`.
6. `treemap_part_whole` uses parent rectangles split into child rectangles. Printed child values are the numeric source of truth; rectangle areas are visual layout and verification uses metadata-backed child values and value-label boxes.
7. `scatter_readout` uses point markers, printed point values, x-axis labels, and a series legend as the source of truth. Evidence projects to the selected point/value label and the x-axis label when the answer is an x label.
8. `waterfall` uses the printed start value, signed contribution labels, connector lines, and final-total value as the source of truth. Cumulative totals are derived from the signed contributions rather than printed at each intermediate step.
9. `candlestick` uses candle bodies, wicks, period labels, and printed O/H/L/C values as the source of truth. Body-range, wick-range, and counterfactual-close answers are verified from metadata-backed open, high, low, and close values.
10. `combo_mark` uses one primary mark encoding plus one overlaid line encoding in the same panel. The primary encoding may be bars, stacked bars, grouped bars, or a filled area; printed exact values are the numeric source of truth for both encodings. Dual-condition count tasks explicitly balance target answers over `1..5`.
11. `pictogram` uses repeated blocks or repeated icons as unit marks. Icon identity is non-semantic; quantity comes from the mark count and the legend unit scale. Evidence uses category-row bounding boxes, not individual icon identity.
12. `radial_progress` uses progress arcs, semicircular gauges, or segmented radial bars on a 0 to 100 scale. Evidence uses widget-card bounding boxes for counted indicators.
13. `parallel_coords` uses vertical metric axes with labeled profile polylines. Axis values increase upward; evidence projects to the profile segments or profile lines needed for the condition, change, or crossing query.
14. `error_interval` uses lower endpoint, midpoint/estimate marker, and upper endpoint metadata as the source of truth. Render variants include horizontal forest-style interval plots, vertical dot-and-whisker plots, and bars with error bars. Evidence uses interval-mark bounding boxes consistently for count and label tasks.
15. `dashboard` includes a trace-backed context-text layer using `assets/context_text/` for non-answer dashboard/report chrome such as headlines, optional main titles, source notes, footer notes, metric snippets, and randomized reserved context boxes. The context boxes may appear as a left sidebar, right sidebar, or bottom band, with per-instance box count, size, and sampled text content recorded in the trace. Context text is excluded from answer semantics, recorded with bboxes/source manifests, and must remain outside the chart-panel evidence contract unless a future task explicitly scopes it in.

## Data Table Grid Notes
1. `table` is the chart scene for row/column/cell data displays.
2. Active task modules live under `trace/tasks/charts/table/`.
3. Defaults live under `configs/domains/charts/table_*.yaml`.
4. Prompt bundles live under `prompts/charts/table_*/`.
5. Public registered task IDs use the `task_charts__table__*` prefix.
6. Keep table evidence prompt-facing as `bbox_set`, with ordering and minimal supporting regions defined by the active task contract.
7. Prompts should name queried rows, columns, cells, years, filters, ranks, or intervals explicitly enough that the supporting bbox evidence is unambiguous.
8. Preserve deterministic bbox ordering whenever prompt order or row order matters.
9. Prefer readable tables over schema complexity: short labels, moderate row/column counts, and style variation through borders, shading, and framing.
