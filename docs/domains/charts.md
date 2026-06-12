# Chart Task Setup

## Purpose
Charts covers numeric, tabular, map, and information-display reasoning tasks where the answer is grounded in a rendered data display. Public task IDs follow `task_charts__<scene_id>__<objective_contract>`, and chart source code is organized as scene packages with one public task file per task id.

## Active Scenes

| Scene | Active tasks |
| --- | ---: |
| `annotated_series` | 1 |
| `area` | 3 |
| `bar_3d` | 8 |
| `boxplot` | 4 |
| `candlestick` | 2 |
| `combo_mark` | 8 |
| `contour_density` | 5 |
| `curve_panels` | 8 |
| `density_curve` | 4 |
| `dashboard` | 9 |
| `dumbbell` | 3 |
| `error_interval` | 3 |
| `errorbar_series` | 3 |
| `heatmap` | 5 |
| `hexbin_density` | 1 |
| `histogram` | 3 |
| `marker_map` | 2 |
| `matrix` | 3 |
| `multiseries` | 7 |
| `parallel_coords` | 4 |
| `part_whole` | 6 |
| `pictogram` | 3 |
| `population_pyramid` | 2 |
| `radar` | 4 |
| `radial_progress` | 4 |
| `radial_sankey` | 2 |
| `region_map` | 11 |
| `sankey` | 4 |
| `scatter_cluster` | 5 |
| `scatter_facet_grid` | 1 |
| `scatter_points` | 3 |
| `scatter_readout` | 3 |
| `scientific_axis_frame` | 2 |
| `single_series` | 13 |
| `size_encoding` | 3 |
| `style_legend` | 3 |
| `small_multiple` | 4 |
| `sunburst` | 4 |
| `surface_3d` | 4 |
| `table` | 8 |
| `treemap` | 2 |
| `uncertainty_band` | 2 |
| `violin` | 3 |
| `waterfall` | 4 |

## Active Tasks

Query IDs are internal replay/review metadata. They are not public sampling units and must not be used to preserve retired broad task IDs.

| Scene | Task ID | Query IDs |
| --- | --- | --- |
| `annotated_series` | `task_charts__annotated_series__callout_endpoint_change_value` | `default` |
| `area` | `task_charts__area__interval_area_value` | `default` |
| `area` | `task_charts__area__stacked_band_dominance_label` | `default` |
| `area` | `task_charts__area__stacked_band_interval_sum_value` | `default` |
| `bar_3d` | `task_charts__bar_3d__category_extremum_gap_value` | `category_extremum_gap_value` |
| `bar_3d` | `task_charts__bar_3d__category_threshold_count` | `category_threshold_count` |
| `bar_3d` | `task_charts__bar_3d__category_total_gap_value` | `category_total_gap_value` |
| `bar_3d` | `task_charts__bar_3d__category_total_value` | `category_total_value` |
| `bar_3d` | `task_charts__bar_3d__pairwise_comparison_count` | `series_comparison_count` |
| `bar_3d` | `task_charts__bar_3d__series_category_scope_total_value` | `series_total_value`, `series_interval_total_value` |
| `bar_3d` | `task_charts__bar_3d__series_threshold_count` | `series_threshold_count` |
| `bar_3d` | `task_charts__bar_3d__series_total_gap_value` | `series_total_gap_value` |
| `boxplot` | `task_charts__boxplot__iqr_extremum_label` | `iqr_extremum_label` |
| `boxplot` | `task_charts__boxplot__median_rank_difference_value` | `default` |
| `boxplot` | `task_charts__boxplot__median_reference_label` | `median_reference_label` |
| `boxplot` | `task_charts__boxplot__paired_median_shift_label` | `default` |
| `candlestick` | `task_charts__candlestick__counterfactual_close_value` | `close_after_body_change_value` |
| `candlestick` | `task_charts__candlestick__range_extremum_label` | `wick_range_extremum_label`, `body_range_extremum_label` |
| `combo_mark` | `task_charts__combo_mark__absolute_gap_extremum_label` | `largest_absolute_gap_label`, `smallest_nonzero_absolute_gap_label` |
| `combo_mark` | `task_charts__combo_mark__conditioned_line_extremum_label` | `max_line_where_primary_above_threshold`, `min_line_where_primary_above_threshold` |
| `combo_mark` | `task_charts__combo_mark__conditioned_primary_extremum_label` | `max_primary_where_line_below_threshold`, `min_primary_where_line_below_threshold` |
| `combo_mark` | `task_charts__combo_mark__cross_mark_difference_value` | `primary_minus_line_at_label`, `line_minus_primary_at_label` |
| `combo_mark` | `task_charts__combo_mark__directional_gap_extremum_label` | `largest_primary_over_line_gap_label`, `largest_line_over_primary_gap_label` |
| `combo_mark` | `task_charts__combo_mark__dual_threshold_condition_count` | `primary_above_and_line_above`, `primary_above_and_line_below`, `primary_below_and_line_above` |
| `combo_mark` | `task_charts__combo_mark__interval_threshold_condition_count` | `primary_between_and_line_above`, `line_between_and_primary_above` |
| `combo_mark` | `task_charts__combo_mark__series_threshold_crossing_label` | `primary_first_above_threshold_label`, `primary_first_below_threshold_label`, `line_first_above_threshold_label`, `line_first_below_threshold_label` |
| `contour_density` | `task_charts__contour_density__density_extremum_region_label` | `density_extremum_region_label` |
| `contour_density` | `task_charts__contour_density__density_threshold_region_count` | `density_threshold_region_count` |
| `contour_density` | `task_charts__contour_density__nearest_region_option_label` | `nearest_region_option_label` |
| `contour_density` | `task_charts__contour_density__reference_distance_extremum_label` | `reference_distance_extremum_label` |
| `contour_density` | `task_charts__contour_density__spread_extremum_region_label` | `spread_extremum_region_label` |
| `curve_panels` | `task_charts__curve_panels__cross_panel_delta_extremum_label` | `cross_panel_delta_extremum_label` |
| `curve_panels` | `task_charts__curve_panels__cross_panel_threshold_earliest_label` | `cross_panel_threshold_earliest_label` |
| `curve_panels` | `task_charts__curve_panels__curve_at_x_extremum_label` | `curve_at_x_extremum_label` |
| `curve_panels` | `task_charts__curve_panels__curve_intersection_count` | `curve_intersection_count` |
| `curve_panels` | `task_charts__curve_panels__earliest_maximum_panel_label` | `earliest_maximum_panel_label` |
| `curve_panels` | `task_charts__curve_panels__panel_curve_threshold_crossing_count` | `panel_curve_threshold_crossing_count` |
| `curve_panels` | `task_charts__curve_panels__panel_point_threshold_count` | `panel_point_threshold_count` |
| `curve_panels` | `task_charts__curve_panels__threshold_series_count` | `threshold_series_count` |
| `density_curve` | `task_charts__density_curve__interval_mass_extremum_label` | `greatest_interval_mass_label`, `least_interval_mass_label` |
| `density_curve` | `task_charts__density_curve__density_at_x_extremum_label` | `highest_density_at_x_label`, `lowest_density_at_x_label` |
| `density_curve` | `task_charts__density_curve__mean_extremum_label` | `highest_mean_label`, `lowest_mean_label` |
| `density_curve` | `task_charts__density_curve__mode_location_extremum_label` | `leftmost_mode_label`, `rightmost_mode_label` |
| `dashboard` | `task_charts__dashboard__category_panel_condition_count` | `category_panel_condition_count` |
| `dashboard` | `task_charts__dashboard__dual_condition_count` | `dual_condition_count` |
| `dashboard` | `task_charts__dashboard__dual_source_target_sum_value` | `dual_source_target_sum_value` |
| `dashboard` | `task_charts__dashboard__panel_gap_extremum_category_label` | `panel_gap_extremum_category_label` |
| `dashboard` | `task_charts__dashboard__shared_label_rank_gap_extremum` | `shared_label_rank_gap_extremum` |
| `dashboard` | `task_charts__dashboard__source_rank_difference_value` | `source_rank_difference_value` |
| `dashboard` | `task_charts__dashboard__source_rank_target_value` | `source_rank_target_value` |
| `dashboard` | `task_charts__dashboard__statement_option_selection_label` | `statement_option_selection_label` |
| `dashboard` | `task_charts__dashboard__top_k_overlap_count` | `top_k_overlap_count` |
| `dumbbell` | `task_charts__dumbbell__absolute_gap_threshold_count` | `absolute_gap_threshold_count` |
| `dumbbell` | `task_charts__dumbbell__gap_rank_row_label` | `gap_rank_row_label` |
| `dumbbell` | `task_charts__dumbbell__side_winner_count` | `side_winner_count` |
| `error_interval` | `task_charts__error_interval__interval_width_rank_label` | `widest_interval_label`, `narrowest_interval_label`, `second_widest_interval_label`, `second_narrowest_interval_label` |
| `error_interval` | `task_charts__error_interval__reference_containment_count` | `contains_reference_count` |
| `error_interval` | `task_charts__error_interval__reference_exclusion_side_count` | `entirely_above_reference_count`, `entirely_below_reference_count` |
| `errorbar_series` | `task_charts__errorbar_series__bound_extremum_x_label` | `highest_upper_bound_x_label`, `lowest_lower_bound_x_label` |
| `errorbar_series` | `task_charts__errorbar_series__same_x_interval_overlap_count` | `overlap_target_errorbar_at_x_count` |
| `errorbar_series` | `task_charts__errorbar_series__threshold_support_count` | `entirely_above_threshold_count`, `entirely_below_threshold_count`, `contains_threshold_count` |
| `heatmap` | `task_charts__heatmap__axis_cell_extremum_label` | `axis_cell_extremum_label` |
| `heatmap` | `task_charts__heatmap__axis_condition_extremum_label` | `axis_condition_extremum_label` |
| `heatmap` | `task_charts__heatmap__colorbar_interval_cell_count` | `colorbar_interval_cell_count` |
| `heatmap` | `task_charts__heatmap__colorbar_threshold_cell_count` | `colorbar_above_threshold_cell_count`, `colorbar_below_threshold_cell_count` |
| `heatmap` | `task_charts__heatmap__condition_run_extremum_label` | `condition_run_extremum_label` |
| `hexbin_density` | `task_charts__hexbin_density__threshold_bin_count` | `above_threshold_bin_count`, `below_threshold_bin_count` |
| `histogram` | `task_charts__histogram__bin_count_between_values` | `bin_count_between_values` |
| `histogram` | `task_charts__histogram__cumulative_rank_bin_label` | `rank_item_bin_label` |
| `histogram` | `task_charts__histogram__interval_mass` | `interval_mass` |
| `marker_map` | `task_charts__marker_map__marker_region_extremum_label` | `marker_region_extremum_label` |
| `marker_map` | `task_charts__marker_map__marker_region_threshold_count` | `marker_region_threshold_count` |
| `matrix` | `task_charts__matrix__axis_extremum_label` | `axis_extremum_label` |
| `matrix` | `task_charts__matrix__off_diagonal_confusion_label` | `off_diagonal_confusion_label` |
| `matrix` | `task_charts__matrix__threshold_cell_count` | `threshold_cell_count` |
| `multiseries` | `task_charts__multiseries__category_total_extremum_label` | `category_total_extremum_label` |
| `multiseries` | `task_charts__multiseries__pair_equality_label` | `pair_equality_label` |
| `multiseries` | `task_charts__multiseries__ranked_change_extremum_label` | `ranked_change_extremum` |
| `multiseries` | `task_charts__multiseries__ranked_pair_ratio_extremum_label` | `ranked_ratio_extremum` |
| `multiseries` | `task_charts__multiseries__ranked_series_share_extremum_label` | `ranked_ratio_extremum` |
| `multiseries` | `task_charts__multiseries__series_comparison_count` | `series_comparison_count` |
| `multiseries` | `task_charts__multiseries__series_rank_at_category_label` | `series_rank_at_category_label` |
| `parallel_coords` | `task_charts__parallel_coords__all_crossings_between_adjacent_axes` | `all_crossings_between_adjacent_axes` |
| `parallel_coords` | `task_charts__parallel_coords__axis_condition_count` | `above_on_both_axes`, `below_on_both_axes`, `above_on_one_below_on_other` |
| `parallel_coords` | `task_charts__parallel_coords__axis_delta_extremum_label` | `largest_increase_between_axes`, `largest_decrease_between_axes`, `largest_absolute_change_between_axes` |
| `parallel_coords` | `task_charts__parallel_coords__crossings_involving_profile_between_axes` | `crossings_involving_profile_between_axes` |
| `part_whole` | `task_charts__part_whole__adjacent_transfer_gap_value` | `chart_order_adjacent_transfer_gap` |
| `part_whole` | `task_charts__part_whole__chart_order_share_to_count` | `chart_order_share_to_count` |
| `part_whole` | `task_charts__part_whole__contiguous_chart_order_sum` | `contiguous_chart_order_sum` |
| `part_whole` | `task_charts__part_whole__positional_segment_share_sum` | `positional_segment_share_sum` |
| `part_whole` | `task_charts__part_whole__sector_share_to_angle` | `sector_share_to_angle` |
| `part_whole` | `task_charts__part_whole__subset_denominator_share_value` | `subset_denominator_share_value` |
| `pictogram` | `task_charts__pictogram__category_total_value` | `category_total_value` |
| `pictogram` | `task_charts__pictogram__group_difference_value` | `group_difference_value` |
| `pictogram` | `task_charts__pictogram__threshold_count` | `threshold_count` |
| `population_pyramid` | `task_charts__population_pyramid__age_group_threshold_count` | `left_side_threshold_count`, `right_side_threshold_count`, `combined_total_threshold_count` |
| `population_pyramid` | `task_charts__population_pyramid__side_gap_extremum_label` | `largest_side_gap_label`, `smallest_nonzero_side_gap_label` |
| `radar` | `task_charts__radar__highlighted_metric_threshold_panel_count` | `highlighted_metric_threshold_panel_count` |
| `radar` | `task_charts__radar__matching_condition_panel_count` | `matching_condition_panel_count` |
| `radar` | `task_charts__radar__profile_advantage_count` | `profile_advantage_count` |
| `radar` | `task_charts__radar__threshold_metric_count_for_panel` | `threshold_metric_count_for_panel` |
| `radial_progress` | `task_charts__radial_progress__extremum_remaining_label` | `highest_remaining_label`, `lowest_remaining_label` |
| `radial_progress` | `task_charts__radial_progress__progress_interval_count` | `within_range_count` |
| `radial_progress` | `task_charts__radial_progress__progress_threshold_count` | `at_least_threshold_count`, `below_threshold_count` |
| `radial_progress` | `task_charts__radial_progress__remaining_threshold_count` | `remaining_at_least_threshold_count` |
| `radial_sankey` | `task_charts__radial_sankey__dominant_endpoint_label` | `largest_target_for_source`, `largest_source_for_target` |
| `radial_sankey` | `task_charts__radial_sankey__transfer_total_value` | `source_to_targets_total`, `sources_to_target_total` |
| `region_map` | `task_charts__region_map__adjacent_category_count` | `adjacent_category_count` |
| `region_map` | `task_charts__region_map__adjacent_numeric_threshold_count` | `adjacent_numeric_threshold_count` |
| `region_map` | `task_charts__region_map__adjacent_same_category_count` | `adjacent_same_category_count` |
| `region_map` | `task_charts__region_map__categorical_region_count` | `categorical_region_count` |
| `region_map` | `task_charts__region_map__continent_category_region_count` | `continent_category_region_count` |
| `region_map` | `task_charts__region_map__continent_region_count` | `continent_region_count` |
| `region_map` | `task_charts__region_map__continent_threshold_region_count` | `continent_threshold_region_count` |
| `region_map` | `task_charts__region_map__group_filtered_region_value` | `group_filtered_region_value` |
| `region_map` | `task_charts__region_map__named_region_set_total_value` | `named_region_set_total_value` |
| `region_map` | `task_charts__region_map__numeric_interval_region_count` | `numeric_interval_region_count` |
| `region_map` | `task_charts__region_map__numeric_threshold_region_count` | `numeric_threshold_region_count` |
| `sankey` | `task_charts__sankey__node_side_total_value` | `source_outgoing_total_flow`, `target_incoming_total_flow` |
| `sankey` | `task_charts__sankey__path_bottleneck_value` | `path_bottleneck_value` |
| `sankey` | `task_charts__sankey__path_flow_difference` | `path_flow_difference` |
| `sankey` | `task_charts__sankey__source_to_target_total_flow` | `source_to_target_total_flow` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_area_rank_label` | `largest_cluster_area_label`, `second_largest_cluster_area_label`, `smallest_cluster_area_label` |
| `scatter_cluster` | `task_charts__scatter_cluster__centroid_option_selection_label` | `centroid_option_selection_label` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_separation_extremum_label` | `cluster_separation_extremum_label` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_spread_extremum_label` | `cluster_spread_extremum_label` |
| `scatter_cluster` | `task_charts__scatter_cluster__cluster_trend_direction_label` | `cluster_trend_direction_label` |
| `scatter_facet_grid` | `task_charts__scatter_facet_grid__region_density_extremum_label` | `upper_right_density_extremum_label`, `upper_left_density_extremum_label`, `lower_right_density_extremum_label`, `lower_left_density_extremum_label` |
| `scatter_points` | `task_charts__scatter_points__axis_threshold_point_count` | `axis_threshold_point_count` |
| `scatter_points` | `task_charts__scatter_points__category_axis_mean_extremum_label` | `category_axis_mean_extremum_label` |
| `scatter_points` | `task_charts__scatter_points__category_threshold_point_count` | `category_threshold_point_count` |
| `scatter_readout` | `task_charts__scatter_readout__series_pair_value_gap_at_x` | `series_pair_value_gap_at_x` |
| `scatter_readout` | `task_charts__scatter_readout__series_x_extremum_label` | `series_highest_x_label`, `series_lowest_x_label` |
| `scatter_readout` | `task_charts__scatter_readout__series_y_anchor_other_series_value` | `series_y_anchor_other_series_value` |
| `single_series` | `task_charts__single_series__baseline_from_aggregate_percent_change` | `baseline_from_aggregate_percent_change` |
| `single_series` | `task_charts__single_series__endpoint_change_value` | `endpoint_change_value` |
| `single_series` | `task_charts__single_series__interval_rate_value` | `interval_rate_value` |
| `single_series` | `task_charts__single_series__interval_value_count` | `in_interval` |
| `single_series` | `task_charts__single_series__monotone_streak_length` | `longest_monotone_streak` |
| `single_series` | `task_charts__single_series__observed_threshold_crossing_label` | `threshold_crossing` |
| `single_series` | `task_charts__single_series__order_statistic_label` | `order_statistic_label` |
| `single_series` | `task_charts__single_series__order_statistic_value` | `order_statistic_value` |
| `single_series` | `task_charts__single_series__projected_threshold_crossing_label` | `threshold_crossing` |
| `single_series` | `task_charts__single_series__remaining_mean_after_removal` | `remaining_mean_after_removal` |
| `single_series` | `task_charts__single_series__target_share_after_removal` | `target_share_after_removal` |
| `single_series` | `task_charts__single_series__threshold_value_count` | `threshold_count` |
| `single_series` | `task_charts__single_series__turning_point_count` | `turning_point_count` |
| `size_encoding` | `task_charts__size_encoding__category_total_extremum_label` | `category_total_extremum_label` |
| `size_encoding` | `task_charts__size_encoding__filtered_item_extremum_label` | `filtered_item_extremum_label` |
| `size_encoding` | `task_charts__size_encoding__reference_size_neighbor_label` | `reference_size_neighbor_label` |
| `scientific_axis_frame` | `task_charts__scientific_axis_frame__axis_span_value` | `x_axis_span_value`, `y_axis_span_value` |
| `scientific_axis_frame` | `task_charts__scientific_axis_frame__tick_spacing_value` | `x_tick_spacing_value`, `y_tick_spacing_value` |
| `style_legend` | `task_charts__style_legend__pairwise_gap_value` | `pairwise_gap_value` |
| `style_legend` | `task_charts__style_legend__threshold_series_count` | `above_threshold_series_count`, `below_threshold_series_count` |
| `style_legend` | `task_charts__style_legend__x_position_extremum_series_label` | `x_position_highest_series_label`, `x_position_lowest_series_label` |
| `small_multiple` | `task_charts__small_multiple__average_top_k_minus_average_bottom_k` | `average_top_k_minus_average_bottom_k` |
| `small_multiple` | `task_charts__small_multiple__composition_shift_l1_distance` | `composition_shift_l1_distance` |
| `small_multiple` | `task_charts__small_multiple__conditioned_panel_sum_from_percent` | `conditioned_panel_sum_from_percent` |
| `small_multiple` | `task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count` | `top_k_by_segment_then_sum_other_segment_count` |
| `sunburst` | `task_charts__sunburst__leaf_range_count_under_parent` | `leaf_range_count_under_parent` |
| `sunburst` | `task_charts__sunburst__leaf_threshold_count_under_parent` | `leaf_threshold_count_under_parent` |
| `sunburst` | `task_charts__sunburst__parent_total_extremum_label` | `highest_parent_total_label`, `lowest_parent_total_label` |
| `sunburst` | `task_charts__sunburst__parent_total_value` | `parent_total_from_leaves_value` |
| `surface_3d` | `task_charts__surface_3d__panel_variation_label` | `panel_variation_label` |
| `surface_3d` | `task_charts__surface_3d__reference_nearest_label` | `reference_nearest_label` |
| `surface_3d` | `task_charts__surface_3d__series_trend_label` | `series_trend_label` |
| `surface_3d` | `task_charts__surface_3d__surface_extremum_label` | `surface_extremum_label` |
| `table` | `task_charts__table__absolute_difference_between_rows_over_year_interval` | `absolute_difference_between_rows_over_year_interval` |
| `table` | `task_charts__table__categorical_value_count` | `categorical_value_count` |
| `table` | `task_charts__table__column_rank_label` | `kth_rank_in_column` |
| `table` | `task_charts__table__column_summary_value` | `column_sum`, `column_mean`, `column_median` |
| `table` | `task_charts__table__filtered_column_mean` | `filtered_column_mean` |
| `table` | `task_charts__table__interval_value_count` | `in_interval` |
| `table` | `task_charts__table__sum_absolute_differences_between_rows_over_year_interval` | `sum_absolute_differences_between_rows_over_year_interval` |
| `table` | `task_charts__table__threshold_count` | `threshold_count` |
| `treemap` | `task_charts__treemap__group_total_value` | `treemap_group_total_value` |
| `treemap` | `task_charts__treemap__repeated_leaf_aggregate_value` | `treemap_repeated_leaf_sum_value`, `treemap_repeated_leaf_average_value` |
| `uncertainty_band` | `task_charts__uncertainty_band__band_overlap_count` | `band_overlap_count` |
| `uncertainty_band` | `task_charts__uncertainty_band__band_width_extremum_x_label` | `widest_band_x_label`, `narrowest_band_x_label` |
| `violin` | `task_charts__violin__modality_label` | `bimodal_label` |
| `violin` | `task_charts__violin__mode_extremum_label` | `highest_mode`, `lowest_mode` |
| `violin` | `task_charts__violin__support_width_extremum_label` | `widest_support`, `narrowest_support` |
| `waterfall` | `task_charts__waterfall__remove_step_final_total` | `remove_step_final_total` |
| `waterfall` | `task_charts__waterfall__reverse_step_final_total` | `reverse_step_final_total` |
| `waterfall` | `task_charts__waterfall__running_total_value` | `running_total_after_step` |
| `waterfall` | `task_charts__waterfall__threshold_crossing_label` | `first_total_at_least_threshold`, `first_total_at_most_threshold` |

## Authoring Notes

- Keep prompt text in external prompt bundles; chart task modules should select scene and task layers, not embed user-facing wording.
- Annotation should mark minimal visual witnesses. Use keyed annotation when roles are ambiguous, such as source vs target marks or paired chart measurements.
- Use shared chart rendering/style helpers for fonts, backgrounds, context text, and protected layout regions before adding scene-specific logic.
- Scientific-paper, arXiv, Matlab-like, appendix, print-scan, and caption-heavy appearances are ordinary chart visual variation. Add them through the shared chart style/treatment/palette/render-parameter sampling path, not as task IDs, query IDs, or separate scenes.
- Plot-like scenes should expose conservative sampled ranges for axes, lines, markers, guide lines, panel borders, and plot fills when their renderer supports shared render-parameter resolution. Do not apply those ranges blindly to maps, Sankey/radial flow charts, pictograms, or other scenes where thinner marks would harm readability.
- Split public task IDs when the program contract changes beyond narrow mirror/parameter branches. Keep those branches in `query_id` only when the prompt, answer schema, annotation schema, and program skeleton remain stable.
- Review artifacts belong under `review/task-reviews/charts/<scene_id>/<task_id>/` and should be inspected in the review app.
