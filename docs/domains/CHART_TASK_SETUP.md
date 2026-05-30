# Chart Task Setup

## Purpose
Charts is the public domain for synthetic data displays, including chart renderers and the `table` scene.

The public taxonomy is `domain -> scene_id -> task_id`. Public `task_id` is the default sampling unit. Query mirrors and semantic branches are recorded as `query_id` and trace params, not public sampling units.

## Active Scenes
- `annotated_series`: 3 active task(s)
- `area`: 3 active task(s)
- `boxplot`: 3 active task(s)
- `candlestick`: 2 active task(s)
- `combo_mark`: 5 active task(s)
- `part_whole`: 2 active task(s)
- `dashboard`: 6 active task(s)
- `table`: 4 active task(s)
- `dumbbell`: 2 active task(s)
- `error_interval`: 2 active task(s)
- `heatmap`: 3 active task(s)
- `histogram`: 2 active task(s)
- `matrix`: 2 active task(s)
- `marker_map`: 2 active task(s)
- `region_map`: 6 active task(s)
- `multiseries`: 3 active task(s)
- `scatter_readout`: 2 active task(s)
- `parallel_coords`: 3 active task(s)
- `pictogram`: 2 active task(s)
- `radar`: 3 active task(s)
- `radial_progress`: 2 active task(s)
- `radial_sankey`: 2 active task(s)
- `sankey`: 2 active task(s)
- `scatter_cluster`: 2 active task(s)
- `curve_panels`: 5 active task(s)
- `single_series`: 8 active task(s)
- `size_encoding`: 3 active task(s)
- `small_multiple`: 2 active task(s)
- `sunburst`: 3 active task(s)
- `bar_3d`: 2 active task(s)
- `surface_3d`: 4 active task(s)
- `treemap`: 2 active task(s)
- `violin`: 1 active task(s)
- `waterfall`: 3 active task(s)

## Active Tasks

| Scene id | Task id | Query id |
|---|---|---|
| `annotated_series` | `task_charts__annotated_series__callout_endpoint_change_value` | `callout_endpoint_change_value` |
| `annotated_series` | `task_charts__annotated_series__event_window_extremum_label` | `event_window_extremum_label` |
| `annotated_series` | `task_charts__annotated_series__event_window_threshold_count` | `event_window_threshold_count` |
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
| `region_map` | `task_charts__region_map__continent_filtered_count` | sampled from `continent_region_count`, `continent_category_region_count`, `continent_threshold_region_count` |
| `region_map` | `task_charts__region_map__group_filtered_region_value` | `group_filtered_region_value` |
| `region_map` | `task_charts__region_map__legend_predicate_region_count` | sampled from `numeric_threshold_region_count`, `numeric_interval_region_count`, `categorical_region_count` |
| `region_map` | `task_charts__region_map__named_region_set_total_value` | `named_region_set_total_value` |
| `marker_map` | `task_charts__marker_map__marker_region_extremum_label` | `marker_region_extremum_label` |
| `marker_map` | `task_charts__marker_map__marker_region_threshold_count` | `marker_region_threshold_count` |
| `part_whole` | `task_charts__part_whole__ordered_segment_value` | sampled from `contiguous_chart_order_sum`, `positional_segment_share_sum`, `chart_order_share_to_count`, `sector_share_to_angle` |
| `part_whole` | `task_charts__part_whole__adjacent_transfer_gap_value` | `chart_order_adjacent_transfer_gap` |
| `dashboard` | `task_charts__dashboard__dual_condition_count` | `dual_condition_count` |
| `dashboard` | `task_charts__dashboard__dual_source_target_sum_value` | `dual_source_target_sum_value` |
| `dashboard` | `task_charts__dashboard__category_panel_condition_count` | `category_panel_condition_count` |
| `dashboard` | `task_charts__dashboard__panel_gap_extremum_category_label` | `panel_gap_extremum_category_label` |
| `dashboard` | `task_charts__dashboard__source_rank_metric_value` | sampled from `source_rank_target_value`, `source_rank_difference_value` |
| `dashboard` | `task_charts__dashboard__top_k_overlap_count` | `top_k_overlap_count` |
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
| `pictogram` | `task_charts__pictogram__group_arithmetic_value` | sampled from `category_total_value`, `group_difference_value` |
| `pictogram` | `task_charts__pictogram__threshold_count` | `threshold_count` |
| `radial_progress` | `task_charts__radial_progress__condition_count` | sampled from `at_least_threshold_count`, `below_threshold_count`, `within_range_count`, `remaining_at_least_threshold_count` |
| `radial_progress` | `task_charts__radial_progress__extremum_remaining_label` | sampled from `highest_remaining_label`, `lowest_remaining_label` |
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
| `treemap` | `task_charts__treemap__group_total_value` | `treemap_group_total_value` |
| `treemap` | `task_charts__treemap__repeated_leaf_aggregate_value` | sampled from `treemap_repeated_leaf_sum_value`, `treemap_repeated_leaf_average_value` |
| `bar_3d` | `task_charts__bar_3d__axis_aggregate_value` | sampled from `series_total_value`, `category_total_value`, `series_interval_total_value`, `series_total_gap_value`, `category_total_gap_value`, `category_extremum_gap_value` |
| `bar_3d` | `task_charts__bar_3d__condition_count` | sampled from `series_threshold_count`, `category_threshold_count`, `series_comparison_count` |
| `surface_3d` | `task_charts__surface_3d__panel_variation_label` | `panel_variation_label` |
| `surface_3d` | `task_charts__surface_3d__reference_nearest_label` | `reference_nearest_label` |
| `surface_3d` | `task_charts__surface_3d__series_trend_label` | `series_trend_label` |
| `surface_3d` | `task_charts__surface_3d__surface_extremum_label` | `surface_extremum_label` |
| `violin` | `task_charts__violin__distribution_feature_label` | sampled from `highest_mode`, `lowest_mode`, `widest_support`, `narrowest_support`, `bimodal_label` |
| `waterfall` | `task_charts__waterfall__counterfactual_final_value` | sampled from `remove_step_final_total`, `reverse_step_final_total` |
| `waterfall` | `task_charts__waterfall__running_total_value` | `running_total_after_step` |
| `waterfall` | `task_charts__waterfall__threshold_crossing_label` | sampled from `first_total_at_least_threshold`, `first_total_at_most_threshold` |

## Refactor Rules
1. The meaningful semantic branch is kept in `query_id` and trace params.
2. `query_id` is an internal replay selector, not a public sampling unit.
3. Chart type, palette, background, row/column axis, largest/smallest, highest/lowest, clockwise/counterclockwise, and other mirror/rendering choices stay internal query or render params.
4. Shared broad generators may remain internal implementation details, but only active public task IDs are registered.
5. Fresh task-review sidecars, browser-app inspection, and solve-rate probes are required for current public task IDs. Workbooks are optional static exports.

## Scene Render Notes
1. `region_map` covers synthetic region maps and bundled Natural Earth-derived geographic maps under `assets/charts/maps/`. Mixed map tasks sample synthetic maps and geographic maps; geographic maps sample world countries, contiguous USA states, EU countries, and China provinces. Filtered-continent and grouped-value tasks are restricted to the world-country asset. Filtered-continent targets `Africa`, `Asia`, `Europe`, `North America`, or `South America`; grouped-value tasks sum printed integer values for visible regions in a named geographic group that satisfy a displayed value condition. Border-neighbor tasks are synthetic-only and count edge-sharing neighbors of one highlighted reference region, excluding corner-only contact. Adjacent-condition tasks are also synthetic-only and count colored neighbors touching a highlighted reference region. Region-set value tasks print visible region labels and integer values, then ask for arithmetic over a named set of labels. `marker_map` reuses the same map assets and synthetic map grammar but encodes values with proportional marker bubbles over labeled regions; public evidence is one `bbox_set` box per answer-bearing marker bubble. Geographic assets supply geometry and geography metadata only; task values, category labels, assignments, and counted regions are synthetic and verified from TRACE metadata. Runtime generation must not download map geometry. The renderer preserves each geographic asset's longitude/latitude aspect ratio, samples map styles, legend placement, and vendored chart fonts, and records selected style metadata under `render_spec.map_render_style`.
2. Chart post-render noise follows the domain policy in `configs/domains/charts/base.yaml`: `apply_prob=0.5` with coordinate-preserving `blur`, `downsample`, `jpeg`, and additive/noise-like edits. The `table` scene uses the chart table group configs under `configs/domains/charts/table_*.yaml`. Scene/task groups should not override this without a documented exception and a trace-level audit.
3. Prompt bundles should use the normal scene/task/query layering. The scene sentence describes what the image shows, task/query text asks for the reasoning target, and answer+evidence prompts must include a named `Evidence format:` section.
4. Prompt text must quote visible named labels when referring to a specific category, series, row, column, panel, region, profile, or endpoint label, for example `"{category_label}"` rather than `{category_label}`. Label-list slot values should quote each listed label.
5. Shared chart label helpers separate dense visual identifiers from semantic names. Dense axis/category marks that are repeated many times should use `sample_chart_labels()`, which draws 2-4 character synthetic IDs from a large unambiguous pool and accepts a task/query namespace to avoid repeated label sets. Legends, series names, panel names, table headers, and map categories that benefit from meaningful text should use `resolve_chart_entity_labels()` or `resolve_chart_category_labels()` with renderer-appropriate width caps. Keep task-local max-character caps tight enough for the renderer, and do not use long natural-language labels on crowded categorical axes.
6. `boxplot` uses keyed point evidence for role-bound comparisons where witness identity matters: reference vs answer boxplot, ranked median witnesses, and before vs after matched boxplots. Single-winner summary queries use a one-point `point_set`. Boxplot axis labels use the dense synthetic ID policy with a tighter 3-character cap because high category counts plus random fonts otherwise create crowded labels.
7. `violin` samples non-semantic violin styling: optional/subtle mode markers, fill style, width/smoothing scale, and single vs per-violin muted palettes. These choices are recorded in `render_spec.violin_style` and must not change the symbolic supports, mode values, or answer/evidence contract.
8. `sunburst` is a not-to-scale concentric hierarchy display. Ring geometry encodes parent/subgroup/leaf structure only; printed outer leaf values are the numeric source of truth, and the render spec records `not_to_scale=true`.
9. `treemap` uses parent rectangles split into child rectangles. Printed child values are the numeric source of truth; rectangle areas are visual layout and verification uses metadata-backed child values and value-label boxes.
10. `scatter_readout` uses point markers, printed point values, x-axis labels, and a series legend as the source of truth. Because the task is explicitly a readout task, public evidence uses `keyed_bbox_map` over role-bound point/value readouts plus the shared x-axis label when needed; legend entries and unrelated readouts remain support text in trace metadata.
11. `waterfall` uses the printed start value, signed contribution labels, connector lines, and final-total value as the source of truth. Cumulative totals are derived from the signed contributions rather than printed at each intermediate step.
12. `candlestick` uses candle bodies, wicks, period labels, and printed O/H/L/C values as the source of truth. Body-range, wick-range, and counterfactual-close answers are verified from metadata-backed open, high, low, and close values. Prompt-facing evidence stays on the minimal candle mark: wick bbox for wick-range queries and body bbox for body-range or counterfactual body-change queries; printed value labels and answer period labels remain support text in trace metadata rather than evidence boxes.
13. `combo_mark` uses one primary mark encoding plus one overlaid line encoding in the same panel. The primary encoding may be bars, stacked bars, grouped bars, or a filled area; printed exact values are the numeric source of truth for both encodings. Dense category labels use compact IDs to avoid axis collisions, chart text samples vendored fonts, and layout jitter is applied through margins so evidence stays aligned. Role-bound primary/line witnesses use `keyed_point_map` evidence keyed as `<category>.primary` and `<category>.line`; printed value labels remain annotations, not public evidence. Label-answer tasks ground only the answer category's two marks. Dual-condition count tasks explicitly balance target answers over `1..5`.
14. `multiseries` uses grouped bars, grouped horizontal bars, multi-line charts, and grouped lollipop charts with a shared category axis and legend-series encodings. Public evidence is `keyed_point_map` keyed as `<category>:<series>` over the supporting mark centers; category labels, legend labels, axis ticks, and printed guide values remain support text/geometry in trace metadata. The scene samples vendored chart fonts while preserving mark geometry and verifier metadata.
15. `part_whole` uses one pie/donut/stacked composition chart plus an exact share table. Prompt-facing evidence is `keyed_point_map` over center points of the supporting chart segments, keyed by visible category labels. The table and displayed total count remain exact numeric inputs and stay in render metadata, but public evidence grounds the chart geometry instead of table rows or readout text.
16. `pictogram` uses repeated blocks or repeated icons as unit marks. Icon identity is non-semantic; quantity comes from the mark count and the legend unit scale. Arithmetic tasks use `keyed_bbox_map` evidence keyed by visible category label over supporting category rows. Threshold-count tasks use homogeneous `bbox_set` evidence over every matching category row. Individual icons remain non-semantic and are not separate public evidence witnesses.
17. `radial_progress` uses progress arcs, semicircular gauges, or segmented radial bars on a 0 to 100 scale. Condition-count evidence uses one homogeneous `bbox_set` widget-card box per counted indicator. Remaining-progress extremum evidence uses one widget-card box for the answer label. The scene samples vendored chart fonts and records the selected font family in render metadata.
18. `radar` uses small-multiple radar panels and single two-profile radar charts. Panel-count tasks use one `bbox_set` panel box per counted panel. Metric-count tasks use `point_set` evidence at counted radar vertices. Two-profile advantage tasks use `point_pair_set` evidence, with each pair marking the two compared profile vertices for one counted metric.
19. `parallel_coords` uses vertical metric axes with labeled profile polylines. Axis values increase upward. Condition-count and delta-label tasks use `keyed_point_map` evidence keyed by visible profile label, with each point placed on the supporting profile segment between the named axes. Crossing-count tasks use homogeneous `point_set` evidence at the counted line-intersection points.
20. `error_interval` uses lower endpoint, midpoint/estimate marker, and upper endpoint metadata as the source of truth. Render variants include horizontal forest-style interval plots, vertical dot-and-whisker plots, and bars with error bars. Evidence uses interval-mark bounding boxes consistently for count and label tasks; boxes should cover the whisker/bar marks, not printed endpoint labels.
21. `heatmap` uses visible cell color levels plus row/column labels as the source of truth. Public evidence remains homogeneous `bbox_set` evidence over heatmap cells: matching cells for condition-count extrema, the candidate row/column cells for cell-extremum lookup, and the winning consecutive run for run tasks. Row/column labels and legend text are support text in trace metadata, not prompt-facing evidence boxes.
22. `histogram` uses one bar per integer x-axis value. Public evidence is homogeneous `bbox_set` evidence over the relevant bars: all bars in or outside a queried interval, all bars in a value-count interval, or the single answer bar for cumulative-rank lookup. Axis labels, guide lines, and tick labels are support text/geometry in trace metadata, not prompt-facing evidence.
23. `matrix` uses printed cell values plus row/column labels as the source of truth. Public evidence is cell-only `bbox_set` evidence: all candidate cells in the queried line for extremum-label tasks, off-diagonal candidate cells for confusion tasks, and only matching cells for threshold-count tasks. Row/column labels and axis titles remain support text in trace metadata, not prompt-facing evidence boxes.
24. `dashboard` includes a trace-backed context-text layer using `assets/context_text/` for non-answer dashboard/report chrome such as headlines, optional main titles, source notes, footer notes, metric snippets, and randomized reserved context boxes. The context boxes may appear as a left sidebar, right sidebar, or bottom band, with per-instance box count, size, and sampled text content recorded in the trace. Context text is excluded from answer semantics, recorded with bboxes/source manifests, and must remain outside the chart-panel evidence contract unless a future task explicitly scopes it in.
25. `dumbbell` uses horizontal paired-dot rows on a shared numeric axis. Public evidence is `bbox_set` over the minimal connector-and-dot pair for each supporting row; row labels, legend labels, and axis tick text remain support text in trace metadata, not evidence boxes. The scene samples vendored chart fonts, mild layout jitter, series/connector colors, and non-answer header wording while preserving row geometry and verifier metadata.
26. `annotated_series` uses a single labeled axis chart with a visible annotation layer. Event-window tasks answer only from marks inside the shaded window and use `point_set` evidence over the value-mark centers used for the answer. The callout endpoint task binds distinct roles with `keyed_point_map` evidence using `callout_mark` and `endpoint_mark`. Highlighted-window and callout boxes remain trace/render metadata locators, not prompt-facing evidence.
27. `scatter_cluster` uses colored point clusters plus a legend. Cluster-level answers are grounded by role-keyed cluster-hull boxes: `answer_cluster` for trend and spread extrema, and `reference_cluster` plus `answer_cluster` for closest/farthest separation queries. Individual point boxes and legend entries remain trace metadata.
28. `single_series` uses one ordered or labeled axis chart rendered as bars, horizontal bars, lines, areas, dot plots, lollipop charts, or scatter-like mark displays depending on the task. Count/streak/statistic/counterfactual tasks use homogeneous `point_set` evidence over supporting mark centers. Endpoint interval-change tasks use `keyed_point_map` evidence with `start_mark` and `end_mark` because endpoint roles matter. Threshold-crossing tasks use `point_set` evidence over the crossing witness prefix, or an empty point set for controlled-unanswerable cases.

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
