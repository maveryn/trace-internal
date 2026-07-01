# Prompt Concision Audit

- rendered prompts: `680`
- tasks covered: `180`
- observed query ids covered: `340`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_charts__annotated_series__callout_endpoint_change_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__area__interval_area_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__area__stacked_band_dominance_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__area__stacked_band_interval_sum_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__category_extremum_gap_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__category_threshold_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__category_total_gap_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__category_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__pairwise_comparison_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__series_category_scope_total_value | `series_interval_total_value, series_total_value` | `{'series_interval_total_value': 1, 'series_total_value': 1}` | 2 | `` |
| task_charts__bar_3d__series_threshold_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__bar_3d__series_total_gap_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__boxplot__iqr_extremum_label | `largest_iqr_label, smallest_iqr_label` | `{'largest_iqr_label': 1, 'smallest_iqr_label': 1}` | 2 | `` |
| task_charts__boxplot__median_rank_difference_value | `median_top_bottom_difference_value, median_top_second_difference_value, median_top_third_difference_value` | `{'median_top_bottom_difference_value': 1, 'median_top_second_difference_value': 1, 'median_top_third_difference_value': 1}` | 3 | `` |
| task_charts__boxplot__paired_median_shift_label | `paired_median_greatest_absolute_change_label, paired_median_greatest_decrease_label, paired_median_greatest_increase_label` | `{'paired_median_greatest_absolute_change_label': 1, 'paired_median_greatest_decrease_label': 1, 'paired_median_greatest_increase_label': 1}` | 3 | `` |
| task_charts__candlestick__counterfactual_close_value | `close_after_body_decrease_value, close_after_body_increase_value` | `{'close_after_body_decrease_value': 1, 'close_after_body_increase_value': 1}` | 2 | `` |
| task_charts__candlestick__range_extremum_label | `largest_body_range_label, largest_wick_range_label, smallest_body_range_label, smallest_wick_range_label` | `{'largest_body_range_label': 1, 'largest_wick_range_label': 1, 'smallest_body_range_label': 1, 'smallest_wick_range_label': 1}` | 4 | `` |
| task_charts__combo_mark__absolute_gap_extremum_label | `largest_absolute_gap_label, smallest_nonzero_absolute_gap_label` | `{'largest_absolute_gap_label': 1, 'smallest_nonzero_absolute_gap_label': 1}` | 2 | `` |
| task_charts__combo_mark__conditioned_line_extremum_label | `max_line_where_primary_above_threshold, min_line_where_primary_above_threshold` | `{'max_line_where_primary_above_threshold': 1, 'min_line_where_primary_above_threshold': 1}` | 2 | `` |
| task_charts__combo_mark__conditioned_primary_extremum_label | `max_primary_where_line_below_threshold, min_primary_where_line_below_threshold` | `{'max_primary_where_line_below_threshold': 1, 'min_primary_where_line_below_threshold': 1}` | 2 | `` |
| task_charts__combo_mark__cross_mark_difference_value | `line_minus_primary_at_label, primary_minus_line_at_label` | `{'line_minus_primary_at_label': 1, 'primary_minus_line_at_label': 1}` | 2 | `` |
| task_charts__combo_mark__directional_gap_extremum_label | `largest_line_over_primary_gap_label, largest_primary_over_line_gap_label` | `{'largest_line_over_primary_gap_label': 1, 'largest_primary_over_line_gap_label': 1}` | 2 | `` |
| task_charts__combo_mark__dual_threshold_condition_count | `primary_above_and_line_above, primary_above_and_line_below, primary_below_and_line_above` | `{'primary_above_and_line_above': 1, 'primary_above_and_line_below': 1, 'primary_below_and_line_above': 1}` | 3 | `` |
| task_charts__combo_mark__interval_threshold_condition_count | `line_between_and_primary_above, primary_between_and_line_above` | `{'line_between_and_primary_above': 1, 'primary_between_and_line_above': 1}` | 2 | `` |
| task_charts__combo_mark__series_threshold_crossing_label | `line_first_above_threshold_label, line_first_below_threshold_label, primary_first_above_threshold_label, primary_first_below_threshold_label` | `{'line_first_above_threshold_label': 1, 'line_first_below_threshold_label': 1, 'primary_first_above_threshold_label': 1, 'primary_first_below_threshold_label': 1}` | 4 | `` |
| task_charts__composition_panels__composition_shift_l1_distance | `single` | `{'single': 1}` | 2 | `` |
| task_charts__composition_panels__conditioned_panel_sum_from_percent | `single` | `{'single': 1}` | 2 | `` |
| task_charts__composition_panels__segment_count_extremum_panel_label | `largest_count, smallest_count` | `{'largest_count': 1, 'smallest_count': 1}` | 2 | `` |
| task_charts__composition_panels__segment_count_nearest_target_panel_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label | `largest_count_gap, smallest_count_gap` | `{'largest_count_gap': 1, 'smallest_count_gap': 1}` | 2 | `` |
| task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__contour_density__density_extremum_region_label | `highest_density_region_label, lowest_density_region_label` | `{'highest_density_region_label': 1, 'lowest_density_region_label': 1}` | 2 | `` |
| task_charts__contour_density__density_threshold_region_count | `density_at_least_threshold_region_count, density_below_threshold_region_count` | `{'density_at_least_threshold_region_count': 1, 'density_below_threshold_region_count': 1}` | 2 | `` |
| task_charts__contour_density__reference_distance_extremum_label | `horizontal_line_farthest_region_label, horizontal_line_nearest_region_label, point_farthest_region_label, point_nearest_region_label, vertical_line_farthest_region_label, vertical_line_nearest_region_label` | `{'horizontal_line_farthest_region_label': 1, 'horizontal_line_nearest_region_label': 1, 'point_farthest_region_label': 1, 'point_nearest_region_label': 1, 'vertical_line_farthest_region_label': 1, 'vertical_line_nearest_region_label': 1}` | 6 | `` |
| task_charts__contour_density__spread_extremum_region_label | `narrowest_spread_region_label, widest_spread_region_label` | `{'narrowest_spread_region_label': 1, 'widest_spread_region_label': 1}` | 2 | `` |
| task_charts__curve_panels__cross_panel_delta_extremum_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__curve_panels__cross_panel_threshold_earliest_label | `cross_panel_downward_threshold_earliest_label, cross_panel_upward_threshold_earliest_label` | `{'cross_panel_downward_threshold_earliest_label': 1, 'cross_panel_upward_threshold_earliest_label': 1}` | 2 | `` |
| task_charts__curve_panels__curve_at_x_extremum_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__curve_panels__curve_intersection_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__curve_panels__earliest_maximum_panel_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__curve_panels__endpoint_rank_panel_label | `end_highest_panel_label, end_lowest_panel_label, start_highest_panel_label, start_lowest_panel_label` | `{'end_highest_panel_label': 1, 'end_lowest_panel_label': 1, 'start_highest_panel_label': 1, 'start_lowest_panel_label': 1}` | 4 | `` |
| task_charts__curve_panels__global_value_extremum_panel_label | `overall_maximum_value_panel_label, overall_minimum_value_panel_label` | `{'overall_maximum_value_panel_label': 1, 'overall_minimum_value_panel_label': 1}` | 2 | `` |
| task_charts__curve_panels__panel_curve_threshold_crossing_count | `panel_curve_downward_threshold_crossing_count, panel_curve_upward_threshold_crossing_count` | `{'panel_curve_downward_threshold_crossing_count': 1, 'panel_curve_upward_threshold_crossing_count': 1}` | 2 | `` |
| task_charts__curve_panels__panel_spread_extremum_label | `largest_panel_spread_label, smallest_panel_spread_label` | `{'largest_panel_spread_label': 1, 'smallest_panel_spread_label': 1}` | 2 | `` |
| task_charts__curve_panels__threshold_series_count | `above_threshold_series_count, below_threshold_series_count` | `{'above_threshold_series_count': 1, 'below_threshold_series_count': 1}` | 2 | `` |
| task_charts__dashboard__category_extremum_panel_label | `largest_category_panel_label, smallest_category_panel_label` | `{'largest_category_panel_label': 1, 'smallest_category_panel_label': 1}` | 2 | `` |
| task_charts__dashboard__category_panel_condition_count | `category_panel_greater_than_threshold_count, category_panel_less_than_threshold_count` | `{'category_panel_greater_than_threshold_count': 1, 'category_panel_less_than_threshold_count': 1}` | 2 | `` |
| task_charts__dashboard__category_total_extremum_label | `largest_category_total_label, smallest_category_total_label` | `{'largest_category_total_label': 1, 'smallest_category_total_label': 1}` | 2 | `` |
| task_charts__dashboard__global_value_extremum_category_label | `global_maximum_value_category_label, global_minimum_value_category_label` | `{'global_maximum_value_category_label': 1, 'global_minimum_value_category_label': 1}` | 2 | `` |
| task_charts__dashboard__panel_total_extremum_label | `largest_panel_total_label, smallest_panel_total_label` | `{'largest_panel_total_label': 1, 'smallest_panel_total_label': 1}` | 2 | `` |
| task_charts__dashboard__panel_value_range_extremum_label | `largest_panel_value_range_label, smallest_panel_value_range_label` | `{'largest_panel_value_range_label': 1, 'smallest_panel_value_range_label': 1}` | 2 | `` |
| task_charts__dashboard__panel_value_range_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__dashboard__source_rank_target_value | `largest_source_rank_target_value, smallest_source_rank_target_value` | `{'largest_source_rank_target_value': 1, 'smallest_source_rank_target_value': 1}` | 2 | `` |
| task_charts__dashboard__statement_option_selection_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__density_curve__density_at_x_extremum_label | `highest_density_at_x_label, lowest_density_at_x_label` | `{'highest_density_at_x_label': 1, 'lowest_density_at_x_label': 1}` | 2 | `` |
| task_charts__density_curve__interval_mass_extremum_label | `greatest_interval_mass_label, least_interval_mass_label` | `{'greatest_interval_mass_label': 1, 'least_interval_mass_label': 1}` | 2 | `` |
| task_charts__density_curve__mean_extremum_label | `highest_mean_label, lowest_mean_label` | `{'highest_mean_label': 1, 'lowest_mean_label': 1}` | 2 | `` |
| task_charts__density_curve__mode_location_extremum_label | `leftmost_mode_label, rightmost_mode_label` | `{'leftmost_mode_label': 1, 'rightmost_mode_label': 1}` | 2 | `` |
| task_charts__dumbbell__absolute_gap_threshold_count | `absolute_gap_at_least_threshold_count, absolute_gap_at_most_threshold_count` | `{'absolute_gap_at_least_threshold_count': 1, 'absolute_gap_at_most_threshold_count': 1}` | 2 | `` |
| task_charts__dumbbell__gap_rank_row_label | `largest_gap_rank_row_label, smallest_gap_rank_row_label` | `{'largest_gap_rank_row_label': 1, 'smallest_gap_rank_row_label': 1}` | 2 | `` |
| task_charts__dumbbell__side_winner_count | `series_a_greater_threshold_count, series_b_greater_threshold_count` | `{'series_a_greater_threshold_count': 1, 'series_b_greater_threshold_count': 1}` | 2 | `` |
| task_charts__error_interval__interval_width_rank_label | `narrowest_interval_label, second_narrowest_interval_label, second_widest_interval_label, widest_interval_label` | `{'narrowest_interval_label': 1, 'second_narrowest_interval_label': 1, 'second_widest_interval_label': 1, 'widest_interval_label': 1}` | 4 | `` |
| task_charts__error_interval__reference_containment_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__error_interval__reference_exclusion_side_count | `entirely_above_reference_count, entirely_below_reference_count` | `{'entirely_above_reference_count': 1, 'entirely_below_reference_count': 1}` | 2 | `` |
| task_charts__errorbar_series__bound_extremum_x_label | `highest_upper_bound_x_label, lowest_lower_bound_x_label` | `{'highest_upper_bound_x_label': 1, 'lowest_lower_bound_x_label': 1}` | 2 | `` |
| task_charts__errorbar_series__same_x_interval_overlap_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__heatmap__axis_cell_extremum_label | `column_coolest_row_label, column_hottest_row_label, row_coolest_column_label, row_hottest_column_label` | `{'column_coolest_row_label': 1, 'column_hottest_row_label': 1, 'row_coolest_column_label': 1, 'row_hottest_column_label': 1}` | 4 | `` |
| task_charts__heatmap__axis_condition_extremum_label | `column_condition_extremum_label, row_condition_extremum_label` | `{'column_condition_extremum_label': 1, 'row_condition_extremum_label': 1}` | 2 | `` |
| task_charts__heatmap__colorbar_interval_cell_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__heatmap__colorbar_threshold_cell_count | `colorbar_above_threshold_cell_count, colorbar_below_threshold_cell_count` | `{'colorbar_above_threshold_cell_count': 1, 'colorbar_below_threshold_cell_count': 1}` | 2 | `` |
| task_charts__heatmap__condition_run_extremum_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__hexbin_density__threshold_bin_count | `above_threshold_bin_count, below_threshold_bin_count` | `{'above_threshold_bin_count': 1, 'below_threshold_bin_count': 1}` | 2 | `` |
| task_charts__histogram__cumulative_rank_bin_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__histogram__interval_mass | `inside_interval_mass, outside_interval_mass` | `{'inside_interval_mass': 1, 'outside_interval_mass': 1}` | 2 | `` |
| task_charts__matrix__axis_extremum_label | `column_highest_axis_extremum_label, column_lowest_axis_extremum_label, row_highest_axis_extremum_label, row_lowest_axis_extremum_label` | `{'column_highest_axis_extremum_label': 1, 'column_lowest_axis_extremum_label': 1, 'row_highest_axis_extremum_label': 1, 'row_lowest_axis_extremum_label': 1}` | 4 | `` |
| task_charts__matrix__off_diagonal_confusion_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__matrix__threshold_cell_count | `column_at_least_threshold_cell_count, column_at_most_threshold_cell_count, row_at_least_threshold_cell_count, row_at_most_threshold_cell_count` | `{'column_at_least_threshold_cell_count': 1, 'column_at_most_threshold_cell_count': 1, 'row_at_least_threshold_cell_count': 1, 'row_at_most_threshold_cell_count': 1}` | 4 | `` |
| task_charts__multiseries__category_total_extremum_label | `largest_category_total_label, smallest_category_total_label` | `{'largest_category_total_label': 1, 'smallest_category_total_label': 1}` | 2 | `` |
| task_charts__multiseries__pair_equality_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__multiseries__ranked_change_extremum_label | `largest_absolute_gap_label, largest_decrease_label, largest_increase_label, smallest_absolute_gap_label` | `{'largest_absolute_gap_label': 1, 'largest_decrease_label': 1, 'largest_increase_label': 1, 'smallest_absolute_gap_label': 1}` | 4 | `` |
| task_charts__multiseries__ranked_pair_ratio_extremum_label | `largest_pair_ratio_label, smallest_pair_ratio_label` | `{'largest_pair_ratio_label': 1, 'smallest_pair_ratio_label': 1}` | 2 | `` |
| task_charts__multiseries__ranked_series_share_extremum_label | `largest_series_share_label, smallest_series_share_label` | `{'largest_series_share_label': 1, 'smallest_series_share_label': 1}` | 2 | `` |
| task_charts__multiseries__series_rank_at_category_label | `largest_series_at_category_label, smallest_series_at_category_label` | `{'largest_series_at_category_label': 1, 'smallest_series_at_category_label': 1}` | 2 | `` |
| task_charts__parallel_coords__all_crossings_between_adjacent_axes | `single` | `{'single': 1}` | 2 | `` |
| task_charts__parallel_coords__axis_condition_count | `above_on_both_axes, above_on_one_below_on_other, below_on_both_axes` | `{'above_on_both_axes': 1, 'above_on_one_below_on_other': 1, 'below_on_both_axes': 1}` | 3 | `` |
| task_charts__parallel_coords__axis_delta_extremum_label | `largest_absolute_change_between_axes, largest_decrease_between_axes, largest_increase_between_axes` | `{'largest_absolute_change_between_axes': 1, 'largest_decrease_between_axes': 1, 'largest_increase_between_axes': 1}` | 3 | `` |
| task_charts__part_whole__adjacent_transfer_gap_value | `clockwise_adjacent_transfer, counterclockwise_adjacent_transfer` | `{'clockwise_adjacent_transfer': 1, 'counterclockwise_adjacent_transfer': 1}` | 2 | `` |
| task_charts__part_whole__contiguous_chart_order_sum | `clockwise_span, counterclockwise_span` | `{'clockwise_span': 1, 'counterclockwise_span': 1}` | 2 | `` |
| task_charts__part_whole__sector_share_to_angle | `clockwise_sector_angle, counterclockwise_sector_angle` | `{'clockwise_sector_angle': 1, 'counterclockwise_sector_angle': 1}` | 2 | `` |
| task_charts__part_whole__subset_denominator_share_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__pictogram__category_total_extremum_label | `largest_total_category_label, smallest_total_category_label` | `{'largest_total_category_label': 1, 'smallest_total_category_label': 1}` | 2 | `` |
| task_charts__pictogram__category_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__pictogram__group_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__pictogram__target_value_nearest_category_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__pictogram__threshold_count | `greater_than_threshold, less_than_threshold` | `{'greater_than_threshold': 1, 'less_than_threshold': 1}` | 2 | `` |
| task_charts__population_pyramid__age_group_threshold_count | `combined_total_at_least_threshold_count, combined_total_at_most_threshold_count, left_side_at_least_threshold_count, left_side_at_most_threshold_count, right_side_at_least_threshold_count, right_side_at_most_threshold_count` | `{'combined_total_at_least_threshold_count': 1, 'combined_total_at_most_threshold_count': 1, 'left_side_at_least_threshold_count': 1, 'left_side_at_most_threshold_count': 1, 'right_side_at_least_threshold_count': 1, 'right_side_at_most_threshold_count': 1}` | 6 | `` |
| task_charts__population_pyramid__dominant_side_count | `left_side_greater_count, right_side_greater_count` | `{'left_side_greater_count': 1, 'right_side_greater_count': 1}` | 2 | `` |
| task_charts__population_pyramid__side_gap_extremum_label | `largest_side_gap_label, smallest_nonzero_side_gap_label` | `{'largest_side_gap_label': 1, 'smallest_nonzero_side_gap_label': 1}` | 2 | `` |
| task_charts__population_pyramid__side_value_extremum_label | `left_side_largest_value_label, left_side_smallest_value_label, right_side_largest_value_label, right_side_smallest_value_label` | `{'left_side_largest_value_label': 1, 'left_side_smallest_value_label': 1, 'right_side_largest_value_label': 1, 'right_side_smallest_value_label': 1}` | 4 | `` |
| task_charts__radar__highlighted_metric_threshold_panel_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__radar__matching_condition_panel_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__radar__profile_advantage_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__radar__threshold_metric_count_for_panel | `single` | `{'single': 1}` | 2 | `` |
| task_charts__radial_progress__extremum_remaining_label | `highest_remaining_label, lowest_remaining_label` | `{'highest_remaining_label': 1, 'lowest_remaining_label': 1}` | 2 | `` |
| task_charts__radial_progress__progress_interval_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__radial_progress__progress_threshold_count | `at_least_threshold_count, below_threshold_count` | `{'at_least_threshold_count': 1, 'below_threshold_count': 1}` | 2 | `` |
| task_charts__radial_sankey__dominant_endpoint_label | `largest_source_for_target, largest_target_for_source` | `{'largest_source_for_target': 1, 'largest_target_for_source': 1}` | 2 | `` |
| task_charts__radial_sankey__transfer_total_value | `source_to_targets_total, sources_to_target_total` | `{'source_to_targets_total': 1, 'sources_to_target_total': 1}` | 2 | `` |
| task_charts__region_map__adjacent_category_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__adjacent_numeric_threshold_count | `greater_than_adjacent_numeric_threshold_count, less_than_adjacent_numeric_threshold_count` | `{'greater_than_adjacent_numeric_threshold_count': 1, 'less_than_adjacent_numeric_threshold_count': 1}` | 2 | `` |
| task_charts__region_map__adjacent_same_category_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__categorical_region_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__group_category_region_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__marker_region_extremum_label | `largest_marker_region_extremum_label, smallest_marker_region_extremum_label` | `{'largest_marker_region_extremum_label': 1, 'smallest_marker_region_extremum_label': 1}` | 2 | `` |
| task_charts__region_map__marker_region_threshold_count | `greater_than_marker_region_threshold_count, less_than_marker_region_threshold_count` | `{'greater_than_marker_region_threshold_count': 1, 'less_than_marker_region_threshold_count': 1}` | 2 | `` |
| task_charts__region_map__named_region_set_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__numeric_interval_region_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__region_map__numeric_threshold_region_count | `greater_than_numeric_threshold_region_count, less_than_numeric_threshold_region_count` | `{'greater_than_numeric_threshold_region_count': 1, 'less_than_numeric_threshold_region_count': 1}` | 2 | `` |
| task_charts__sankey__node_side_total_value | `source_outgoing_total_flow, target_incoming_total_flow` | `{'source_outgoing_total_flow': 1, 'target_incoming_total_flow': 1}` | 2 | `` |
| task_charts__sankey__path_bottleneck_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__sankey__source_to_target_total_flow | `single` | `{'single': 1}` | 2 | `` |
| task_charts__scatter_cluster__centroid_option_selection_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__scatter_cluster__cluster_area_rank_label | `largest_cluster_area_label, smallest_cluster_area_label` | `{'largest_cluster_area_label': 1, 'smallest_cluster_area_label': 1}` | 2 | `` |
| task_charts__scatter_cluster__cluster_spread_extremum_label | `largest_horizontal_spread_label, largest_overall_spread_label, largest_vertical_spread_label, smallest_horizontal_spread_label, smallest_overall_spread_label, smallest_vertical_spread_label` | `{'largest_horizontal_spread_label': 1, 'largest_overall_spread_label': 1, 'largest_vertical_spread_label': 1, 'smallest_horizontal_spread_label': 1, 'smallest_overall_spread_label': 1, 'smallest_vertical_spread_label': 1}` | 6 | `` |
| task_charts__scatter_cluster__cluster_trend_direction_label | `downward_trend_label, upward_trend_label` | `{'downward_trend_label': 1, 'upward_trend_label': 1}` | 2 | `` |
| task_charts__scatter_points__axis_threshold_point_count | `x_above_threshold_count, x_below_threshold_count, y_above_threshold_count, y_below_threshold_count` | `{'x_above_threshold_count': 1, 'x_below_threshold_count': 1, 'y_above_threshold_count': 1, 'y_below_threshold_count': 1}` | 4 | `` |
| task_charts__scatter_points__category_axis_mean_extremum_label | `largest_mean_x_category_label, largest_mean_y_category_label, smallest_mean_x_category_label, smallest_mean_y_category_label` | `{'largest_mean_x_category_label': 1, 'largest_mean_y_category_label': 1, 'smallest_mean_x_category_label': 1, 'smallest_mean_y_category_label': 1}` | 4 | `` |
| task_charts__scatter_points__category_threshold_point_count | `category_x_above_threshold_count, category_x_below_threshold_count, category_y_above_threshold_count, category_y_below_threshold_count` | `{'category_x_above_threshold_count': 1, 'category_x_below_threshold_count': 1, 'category_y_above_threshold_count': 1, 'category_y_below_threshold_count': 1}` | 4 | `` |
| task_charts__scatter_readout__series_pair_value_gap_at_x | `single` | `{'single': 1}` | 2 | `` |
| task_charts__scatter_readout__series_value_at_x_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__scatter_readout__series_x_extremum_label | `series_highest_x_label, series_lowest_x_label` | `{'series_highest_x_label': 1, 'series_lowest_x_label': 1}` | 2 | `` |
| task_charts__scatter_readout__series_y_anchor_other_series_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__scatter_readout__x_value_rank_series_label | `x_highest_series_label, x_lowest_series_label` | `{'x_highest_series_label': 1, 'x_lowest_series_label': 1}` | 2 | `` |
| task_charts__scientific_axis_frame__axis_span_value | `x_axis_span_value, y_axis_span_value` | `{'x_axis_span_value': 1, 'y_axis_span_value': 1}` | 2 | `` |
| task_charts__scientific_axis_frame__tick_spacing_value | `x_first_tick_spacing_value, x_last_tick_spacing_value, y_first_tick_spacing_value, y_last_tick_spacing_value` | `{'x_first_tick_spacing_value': 1, 'x_last_tick_spacing_value': 1, 'y_first_tick_spacing_value': 1, 'y_last_tick_spacing_value': 1}` | 4 | `` |
| task_charts__single_series__endpoint_change_value | `absolute_endpoint_change_value, percent_endpoint_change_value, signed_endpoint_change_value` | `{'absolute_endpoint_change_value': 1, 'percent_endpoint_change_value': 1, 'signed_endpoint_change_value': 1}` | 3 | `` |
| task_charts__single_series__interval_rate_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__single_series__interval_value_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__single_series__monotone_streak_length | `longest_decreasing_streak_length, longest_increasing_streak_length` | `{'longest_decreasing_streak_length': 1, 'longest_increasing_streak_length': 1}` | 2 | `` |
| task_charts__single_series__observed_threshold_crossing_label | `observed_above_threshold_crossing_label, observed_below_threshold_crossing_label` | `{'observed_above_threshold_crossing_label': 1, 'observed_below_threshold_crossing_label': 1}` | 2 | `` |
| task_charts__single_series__order_statistic_label | `median_order_statistic_label, nth_highest_order_statistic_label, nth_lowest_order_statistic_label` | `{'median_order_statistic_label': 1, 'nth_highest_order_statistic_label': 1, 'nth_lowest_order_statistic_label': 1}` | 3 | `` |
| task_charts__single_series__order_statistic_value | `median_order_statistic_value, nth_highest_order_statistic_value, nth_lowest_order_statistic_value` | `{'median_order_statistic_value': 1, 'nth_highest_order_statistic_value': 1, 'nth_lowest_order_statistic_value': 1}` | 3 | `` |
| task_charts__single_series__remaining_mean_after_removal | `single` | `{'single': 1}` | 2 | `` |
| task_charts__single_series__target_share_after_removal | `single` | `{'single': 1}` | 2 | `` |
| task_charts__single_series__threshold_value_count | `above_threshold_count, below_threshold_count` | `{'above_threshold_count': 1, 'below_threshold_count': 1}` | 2 | `` |
| task_charts__single_series__turning_point_count | `peak_turning_point_count, trough_turning_point_count` | `{'peak_turning_point_count': 1, 'trough_turning_point_count': 1}` | 2 | `` |
| task_charts__size_encoding__category_relative_size_count | `larger_than_reference_in_category_count, smaller_than_reference_in_category_count` | `{'larger_than_reference_in_category_count': 1, 'smaller_than_reference_in_category_count': 1}` | 2 | `` |
| task_charts__size_encoding__filtered_item_extremum_label | `largest_size_item_in_category_label, smallest_size_item_in_category_label` | `{'largest_size_item_in_category_label': 1, 'smallest_size_item_in_category_label': 1}` | 2 | `` |
| task_charts__size_encoding__global_item_extremum_category_label | `largest_overall_size_category_label, smallest_overall_size_category_label` | `{'largest_overall_size_category_label': 1, 'smallest_overall_size_category_label': 1}` | 2 | `` |
| task_charts__size_encoding__panel_category_extremum_panel_label | `largest_category_item_panel_label, smallest_category_item_panel_label` | `{'largest_category_item_panel_label': 1, 'smallest_category_item_panel_label': 1}` | 2 | `` |
| task_charts__style_legend__series_extremum_x_label | `series_highest_x_label, series_lowest_x_label` | `{'series_highest_x_label': 1, 'series_lowest_x_label': 1}` | 2 | `` |
| task_charts__style_legend__threshold_series_count | `above_threshold_series_count, below_threshold_series_count` | `{'above_threshold_series_count': 1, 'below_threshold_series_count': 1}` | 2 | `` |
| task_charts__style_legend__x_position_extremum_series_label | `x_position_highest_series_label, x_position_lowest_series_label` | `{'x_position_highest_series_label': 1, 'x_position_lowest_series_label': 1}` | 2 | `` |
| task_charts__sunburst__leaf_range_count_under_parent | `single` | `{'single': 1}` | 2 | `` |
| task_charts__sunburst__leaf_threshold_count_under_parent | `above_threshold_leaf_count_under_parent, below_threshold_leaf_count_under_parent` | `{'above_threshold_leaf_count_under_parent': 1, 'below_threshold_leaf_count_under_parent': 1}` | 2 | `` |
| task_charts__sunburst__parent_total_extremum_label | `highest_parent_total_label, lowest_parent_total_label` | `{'highest_parent_total_label': 1, 'lowest_parent_total_label': 1}` | 2 | `` |
| task_charts__sunburst__parent_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__surface_3d__panel_variation_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__surface_3d__reference_nearest_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__surface_3d__series_trend_label | `decrease, increase` | `{'decrease': 1, 'increase': 1}` | 2 | `` |
| task_charts__table__absolute_difference_between_rows_over_year_interval | `single` | `{'single': 1}` | 2 | `` |
| task_charts__table__categorical_value_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__table__column_rank_label | `highest_rank_in_column, lowest_rank_in_column` | `{'highest_rank_in_column': 1, 'lowest_rank_in_column': 1}` | 2 | `` |
| task_charts__table__column_summary_value | `column_mean, column_median, column_sum` | `{'column_mean': 1, 'column_median': 1, 'column_sum': 1}` | 3 | `` |
| task_charts__table__filtered_column_mean | `above_threshold_filtered_mean, below_threshold_filtered_mean, interval_filtered_mean` | `{'above_threshold_filtered_mean': 1, 'below_threshold_filtered_mean': 1, 'interval_filtered_mean': 1}` | 3 | `` |
| task_charts__table__interval_value_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__table__sum_absolute_differences_between_rows_over_year_interval | `single` | `{'single': 1}` | 2 | `` |
| task_charts__table__threshold_count | `above_threshold_count, below_threshold_count` | `{'above_threshold_count': 1, 'below_threshold_count': 1}` | 2 | `` |
| task_charts__treemap__group_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_charts__treemap__parent_total_extremum_label | `largest_parent_total, smallest_parent_total` | `{'largest_parent_total': 1, 'smallest_parent_total': 1}` | 2 | `` |
| task_charts__treemap__repeated_leaf_aggregate_value | `treemap_repeated_leaf_average_value, treemap_repeated_leaf_sum_value` | `{'treemap_repeated_leaf_average_value': 1, 'treemap_repeated_leaf_sum_value': 1}` | 2 | `` |
| task_charts__uncertainty_band__band_overlap_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__uncertainty_band__band_width_extremum_x_label | `narrowest_band_x_label, widest_band_x_label` | `{'narrowest_band_x_label': 1, 'widest_band_x_label': 1}` | 2 | `` |
| task_charts__violin__modality_label | `single` | `{'single': 1}` | 2 | `` |
| task_charts__violin__mode_extremum_label | `highest_mode, lowest_mode` | `{'highest_mode': 1, 'lowest_mode': 1}` | 2 | `` |
| task_charts__violin__support_width_extremum_label | `narrowest_support, widest_support` | `{'narrowest_support': 1, 'widest_support': 1}` | 2 | `` |
| task_charts__waterfall__remove_step_final_total | `single` | `{'single': 1}` | 2 | `` |
| task_charts__waterfall__reverse_step_final_total | `single` | `{'single': 1}` | 2 | `` |
| task_charts__waterfall__running_total_extremum_value | `maximum_running_total, minimum_running_total` | `{'maximum_running_total': 1, 'minimum_running_total': 1}` | 2 | `` |
| task_charts__waterfall__running_total_value | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_charts__dashboard__category_total_extremum_label / answer_and_annotation / sample 7396521182563627

- `query_id`: `largest_category_total_label`
- `instance_seed`: `7396521182563627`
- `word_count`: `152`
- `body_word_count`: `80`

```text
The image shows a dashboard with 6 titled panels named "Drena Donut", "Patak Bar", "Record Line", "Xanti Line", "Almatine Radar", and "Rickard Radar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Sum each category across every panel. Which category has the largest total? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on that category's mark in every panel; if the answer is "unanswerable", use an empty array.
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"annotation":[[180,220],[475,240],[790,260],[1080,245]],"answer":"Mica"}
```

### task_charts__dashboard__category_total_extremum_label / answer_and_annotation / sample 2728616631873392

- `query_id`: `smallest_category_total_label`
- `instance_seed`: `2728616631873392`
- `word_count`: `149`
- `body_word_count`: `81`

```text
The image shows a dashboard with 7 titled panels named "Compiler Donut", "Optimizer Donut", "Fusion Line", "Clocking Line", "Network Radar", "Accuracy Bar", and "Debug Bar". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the smallest total across all dashboard panels? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Required annotation format: set "annotation" to an array of [x,y] pixel points on that category's mark in every panel; if the answer is "unanswerable", use an empty array.
Required answer format: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"annotation":[[180,220],[475,240],[790,260],[1080,245]],"answer":"Mica"}
```

### task_charts__dashboard__panel_value_range_extremum_label / answer_and_annotation / sample 2709582525960747

- `query_id`: `largest_panel_value_range_label`
- `instance_seed`: `2709582525960747`
- `word_count`: `124`
- `body_word_count`: `66`

```text
The image shows a dashboard with 8 titled panels named "Cesaro Line", "Linga Line", "Savoy Line", "Calleigh Bar", "Matas Bar", "Hying Radar", "Kahmila Radar", and "Handerhan Line". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Across the dashboard, which panel has the greatest difference between its largest and smallest category values?
Format for the "annotation" field: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on the two category marks that define the answer panel's range.
Format for the "answer" field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":"Orchid Bar"}
```

### task_charts__dumbbell__side_winner_count / answer_and_annotation / sample 6842348674244685

- `query_id`: `series_a_greater_threshold_count`
- `instance_seed`: `6842348674244685`
- `word_count`: `123`
- `body_word_count`: `57`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Oyster" at least 16 units greater than "Steers"?
Format for the "annotation" field: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__curve_panels__cross_panel_delta_extremum_label / answer_and_annotation / sample 6477803644536500

- `query_id`: `single`
- `instance_seed`: `6477803644536500`
- `word_count`: `122`
- `body_word_count`: `52`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Using method "Daniyal", find the subplot with the maximum upward change between x = 10 and x = 40. If that method is not plotted in every subplot, treat the question as unanswerable and set the answer to exactly "unanswerable".
Required annotation format: set "annotation" to an object mapping "start_point" and "end_point" to [x,y] pixel points on the answer subplot's selected method markers; if the answer is "unanswerable", use an empty object.
Final answer format: set "answer" to the exact visible subplot label as a string, or "unanswerable" if the requested method is not plotted in every subplot.
Example JSON:
{"annotation":{"start_point":[220,360],"end_point":[460,250]},"answer":"Trade"}
```

### task_charts__dumbbell__absolute_gap_threshold_count / answer_and_annotation / sample 7753372545278570

- `query_id`: `absolute_gap_at_least_threshold_count`
- `instance_seed`: `7753372545278570`
- `word_count`: `120`
- `body_word_count`: `58`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many categories have the two series differing by at least 28 units?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__absolute_gap_threshold_count / answer_and_annotation / sample 2511738239517459

- `query_id`: `absolute_gap_at_most_threshold_count`
- `instance_seed`: `2511738239517459`
- `word_count`: `120`
- `body_word_count`: `60`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Using the shared horizontal axis, how many rows have a dot-to-dot separation at most 20?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__side_winner_count / answer_and_annotation / sample 6024682079833462

- `query_id`: `series_b_greater_threshold_count`
- `instance_seed`: `6024682079833462`
- `word_count`: `119`
- `body_word_count`: `57`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Hillis" greater than "Modrall" by at least 16?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__combo_mark__conditioned_line_extremum_label / answer_and_annotation / sample 8023167637589174

- `query_id`: `max_line_where_primary_above_threshold`
- `instance_seed`: `8023167637589174`
- `word_count`: `118`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Tickets" on the left axis and the overlaid line shows "Apparel" on the right axis. Each category has printed values for both series. Among categories where "Tickets" is above 39, which category has the highest "Apparel" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_line_extremum_label / answer_and_annotation / sample 8442721128581216

- `query_id`: `min_line_where_primary_above_threshold`
- `instance_seed`: `8442721128581216`
- `word_count`: `118`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Support" on the left axis and the overlaid line shows "Devices" on the right axis. Each category has printed values for both series. Among categories where "Support" is above 70, which category has the lowest "Devices" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__absolute_gap_extremum_label / answer_and_annotation / sample 1105819069109579

- `query_id`: `smallest_nonzero_absolute_gap_label`
- `instance_seed`: `1105819069109579`
- `word_count`: `116`
- `body_word_count`: `47`

```text
The image shows a combo chart where vertical bars show "Quartz" on the left axis and the overlaid line shows "Valley" on the right axis. Each category has printed values for both series. Find the category where the two series values differ by the smallest nonzero amount.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__bar_3d__pairwise_comparison_count / answer_and_annotation / sample 8494785466052992

- `query_id`: `single`
- `instance_seed`: `8494785466052992`
- `word_count`: `115`
- `body_word_count`: `46`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For the pair "Spargur" and "Tracey", how many displayed categories have the first series higher than the second?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the top-center point on the first series bar and the top-center point on the second series bar for one counted category; use [] if no categories match.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[210,360],[210,260]],[[320,330],[320,240]],[[430,300],[430,220]]],"answer":3}
```

### task_charts__dashboard__panel_value_range_extremum_label / answer_and_annotation / sample 1569723762398953

- `query_id`: `smallest_panel_value_range_label`
- `instance_seed`: `1569723762398953`
- `word_count`: `115`
- `body_word_count`: `61`

```text
The image shows a dashboard with 6 titled panels named "Dallary Donut", "Eugune Radar", "Quinty Line", "Chrishayla Line", "Zahkir Donut", and "Zavonte Line". It uses a shared category/color key with 8 possible category labels, and exact integer values are shown for each plotted category mark. Find the panel whose category values span the narrowest range. What is its panel title?
Required annotation format: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on the two category marks that define the answer panel's range.
Required answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":"Orchid Bar"}
```

### task_charts__combo_mark__conditioned_primary_extremum_label / answer_and_annotation / sample 8992111285610397

- `query_id`: `min_primary_where_line_below_threshold`
- `instance_seed`: `8992111285610397`
- `word_count`: `114`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "River" and the overlaid line shows "Beacon" on the same value axis. Each category has printed values for both series. Among categories where "Beacon" is below 33, which category has the lowest "River" value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__dashboard__category_total_extremum_label / answer_only / sample 2728616631873392

- `query_id`: `smallest_category_total_label`
- `instance_seed`: `2728616631873392`
- `word_count`: `113`
- `body_word_count`: `81`

```text
The image shows a dashboard with 7 titled panels named "Compiler Donut", "Optimizer Donut", "Fusion Line", "Clocking Line", "Network Radar", "Accuracy Bar", and "Debug Bar". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the smallest total across all dashboard panels? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"answer":"Mica"}
```

### task_charts__combo_mark__directional_gap_extremum_label / answer_and_annotation / sample 6934222898042463

- `query_id`: `largest_primary_over_line_gap_label`
- `instance_seed`: `6934222898042463`
- `word_count`: `112`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Pearl" and the overlaid line shows "Valley" on the same value axis. Each category has printed values for both series. Which category has the largest positive gap where "Pearl" is greater than "Valley"?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__dashboard__category_total_extremum_label / answer_only / sample 7396521182563627

- `query_id`: `largest_category_total_label`
- `instance_seed`: `7396521182563627`
- `word_count`: `112`
- `body_word_count`: `80`

```text
The image shows a dashboard with 6 titled panels named "Drena Donut", "Patak Bar", "Record Line", "Xanti Line", "Almatine Radar", and "Rickard Radar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Sum each category across every panel. Which category has the largest total? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"answer":"Mica"}
```

### task_charts__dashboard__panel_total_extremum_label / answer_and_annotation / sample 794730572079354

- `query_id`: `largest_panel_total_label`
- `instance_seed`: `794730572079354`
- `word_count`: `111`
- `body_word_count`: `63`

```text
The image shows a dashboard with 8 titled panels named "SampleA Bar", "BatchC Donut", "ModelB Line", "RunC Radar", "BatchB Bar", "TrialB Line", "ModelC Donut", and "VariantC Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Sum the category values within each panel. Which panel has the largest total?
Annotation format: set "annotation" to an array of [x,y] pixel points on every category mark in the answer panel.
Final answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[[430,218],[512,337],[588,260],[642,232]],"answer":"Orchid Bar"}
```

### task_charts__combo_mark__cross_mark_difference_value / answer_and_annotation / sample 6678089473717765

- `query_id`: `primary_minus_line_at_label`
- `instance_seed`: `6678089473717765`
- `word_count`: `110`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Media" and the overlaid line shows "Bakery" on the same value axis. Each category has printed values for both series. At category "ZW7", what is the "Media" value minus the "Bakery" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the queried category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same category.
Answer format: set "answer" to the requested signed difference as an integer.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":12}
```

### task_charts__multiseries__ranked_series_share_extremum_label / answer_and_annotation / sample 5688767160430220

- `query_id`: `smallest_series_share_label`
- `instance_seed`: `5688767160430220`
- `word_count`: `110`
- `body_word_count`: `48`

```text
The figure shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Which category label has the smallest percentage share for "Onl" out of that category's total across all series?
Format for the "annotation" field: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark in the answer category.
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,240],"K4M8:Vega":[300,320],"K4M8:Tana":[300,400]},"answer":"K4M8"}
```

### task_charts__combo_mark__directional_gap_extremum_label / answer_and_annotation / sample 1859135762442502

- `query_id`: `largest_line_over_primary_gap_label`
- `instance_seed`: `1859135762442502`
- `word_count`: `109`
- `body_word_count`: `39`

```text
The image shows a combo chart where each stacked bar's printed total shows "Grocery", and the overlaid line shows "Telecom". Each category has printed values for both series. Find the category where "Telecom" exceeds "Grocery" by the largest amount.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__dashboard__panel_value_range_value / answer_and_annotation / sample 4676936198073555

- `query_id`: `single`
- `instance_seed`: `4676936198073555`
- `word_count`: `109`
- `body_word_count`: `59`

```text
The image shows a dashboard with 5 titled panels named "Gunns Radar", "Rinnah Donut", "Hayk Line", "Overlie Line", and "Rua Bar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Using only "Overlie Line", what range do its category values span from smallest to largest?
Format for the "annotation" field: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on those category marks in the named panel.
Format for the "answer" field: set "answer" to the requested integer difference.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":37}
```

### task_charts__dumbbell__gap_rank_row_label / answer_and_annotation / sample 5303107782709320

- `query_id`: `largest_gap_rank_row_label`
- `instance_seed`: `5303107782709320`
- `word_count`: `109`
- `body_word_count`: `66`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Rank rows by the absolute length of the gray connector between the two dots. Which row has the second largest gap?
Annotation format: set "annotation" to one segment [[x1, y1], [x2, y2]], using the two colored dot centers for the supporting row.
Answer format: set "answer" to the exact visible row label as a string.
Example JSON:
{"annotation":[[276,231],[1032,231]],"answer":"Harbor"}
```

### task_charts__dashboard__panel_total_extremum_label / answer_and_annotation / sample 152854471729228

- `query_id`: `smallest_panel_total_label`
- `instance_seed`: `152854471729228`
- `word_count`: `108`
- `body_word_count`: `61`

```text
The image shows a dashboard with 8 titled panels named "Ivory Line", "Summit Radar", "Atlas Radar", "Valley Bar", "Cedar Bar", "Flint Radar", "Crimson Radar", and "Harbor Line". It uses a shared category/color key with 4 possible category labels, and exact integer values are shown for each plotted category mark. Which panel title corresponds to the lowest total over its categories?
Annotation format: set "annotation" to an array of [x,y] pixel points on every category mark in the answer panel.
Answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[[430,218],[512,337],[588,260],[642,232]],"answer":"Orchid Bar"}
```

### task_charts__dashboard__source_rank_target_value / answer_and_annotation / sample 8571842837276742

- `query_id`: `smallest_source_rank_target_value`
- `instance_seed`: `8571842837276742`
- `word_count`: `108`
- `body_word_count`: `58`

```text
The image shows a dashboard with 4 titled panels named "Spectrum Line", "Bayes Line", "Hypothesis Line", and "Timestep Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. First rank categories in "Bayes Line"; for the smallest one, what value appears in "Hypothesis Line"?
Format for the "annotation" field: set "annotation" to an object mapping "source_panel" and "target_panel" to [x,y] pixel points on the selected category marks in those panels.
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"annotation":{"source_panel":[180,220],"target_panel":[860,260]},"answer":47}
```

## Repeated Scaffolding Terms

### task_charts__part_whole__adjacent_transfer_gap_value / answer_and_annotation / sample 1351893675659305

- `query_id`: `counterclockwise_adjacent_transfer`
- `instance_seed`: `1351893675659305`
- `word_count`: `92`
- `body_word_count`: `39`
- `repeated_terms`: `{'chart': 3}`

```text
The chart shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Flint" and target its immediate counterclockwise neighbor. After moving 5 points from source to target, what share gap remains?
Annotation format: set "annotation" to an object mapping the source category label and adjacent target category label to [x,y] pixel points at the centers of their chart segments.
Final answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"annotation":{"Ruby":[590,250],"Crimson":[740,380]},"answer":13}
```

### task_charts__part_whole__sector_share_to_angle / answer_and_annotation / sample 2052361666976211

- `query_id`: `clockwise_sector_angle`
- `instance_seed`: `2052361666976211`
- `word_count`: `92`
- `body_word_count`: `33`
- `repeated_terms`: `{'chart': 3}`

```text
The chart shows one pie chart with a table of exact integer category shares. Moving clockwise around the chart, what central angle in degrees is covered from category "Kitchen" through category "Pharmacy", inclusive?
Format for the "annotation" field: set "annotation" to an object mapping each included category label to the [x,y] pixel point at the center of its chart segment.
Format for the "answer" field: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472]},"answer":108}
```

### task_charts__matrix__axis_extremum_label / answer_only / sample 1148800707456799

- `query_id`: `column_lowest_axis_extremum_label`
- `instance_seed`: `1148800707456799`
- `word_count`: `61`
- `body_word_count`: `57`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a labeled confusion matrix with printed integer counts in each active cell. For column "23Q3", what row label has the cell with the second-lowest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / answer_only / sample 1771124583331139

- `query_id`: `row_highest_axis_extremum_label`
- `instance_seed`: `1771124583331139`
- `word_count`: `58`
- `body_word_count`: `54`
- `repeated_terms`: `{'answer': 3}`

```text
The visual shows a labeled triangular pairwise matrix where only the filled cells count. Within the row labeled "Zambia", which column has the second-highest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__part_whole__adjacent_transfer_gap_value / answer_only / sample 1351893675659305

- `query_id`: `counterclockwise_adjacent_transfer`
- `instance_seed`: `1351893675659305`
- `word_count`: `55`
- `body_word_count`: `39`
- `repeated_terms`: `{'chart': 3}`

```text
The chart shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Flint" and target its immediate counterclockwise neighbor. After moving 5 points from source to target, what share gap remains?
Answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"answer":13}
```

### task_charts__part_whole__sector_share_to_angle / answer_only / sample 2052361666976211

- `query_id`: `clockwise_sector_angle`
- `instance_seed`: `2052361666976211`
- `word_count`: `51`
- `body_word_count`: `33`
- `repeated_terms`: `{'chart': 3}`

```text
The chart shows one pie chart with a table of exact integer category shares. Moving clockwise around the chart, what central angle in degrees is covered from category "Kitchen" through category "Pharmacy", inclusive?
Answer format: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"answer":108}
```

## All Prompt Samples

### task_charts__annotated_series__callout_endpoint_change_value / single / answer_and_annotation / sample 8371341504668071

- `instance_seed`: `8371341504668071`
- `word_count`: `76`
- `body_word_count`: `29`

```text
The chart is a labeled lollipop chart with one visible annotation. Use the mark indicated by the callout and the mark labeled "L7Z2". What is their absolute value difference?
Final answer format: set "answer" to the requested absolute change as an integer.
Annotation format: set "annotation" to an object mapping "callout_mark" and "endpoint_mark" to [x, y] pixel points at the centers of those two marks.
Example JSON:
{"annotation":{"callout_mark":[412,220],"endpoint_mark":[656,344]},"answer":24}
```

### task_charts__annotated_series__callout_endpoint_change_value / single / answer_only / sample 8371341504668071

- `instance_seed`: `8371341504668071`
- `word_count`: `48`
- `body_word_count`: `29`

```text
The chart is a labeled lollipop chart with one visible annotation. Use the mark indicated by the callout and the mark labeled "L7Z2". What is their absolute value difference?
Format for the "answer" field: set "answer" to the requested absolute change as an integer.
Example JSON:
{"answer":24}
```

### task_charts__area__interval_area_value / single / answer_and_annotation / sample 6451018316265519

- `instance_seed`: `6451018316265519`
- `word_count`: `96`
- `body_word_count`: `43`

```text
The visual shows one filled area chart with labeled x-axis positions and numeric values shown at the points. Compute the area under the area chart from "LIMN" to "LDXC": for each adjacent x-axis pair, average the two point values, then sum those averages.
Annotation format: set "annotation" to [x, y] pixel points at the centers of the data point markers from the first queried x-axis label through the second queried x-axis label.
Answer field: set "answer" to the requested area as an integer.
Example JSON:
{"annotation":[[180,420],[280,360],[380,300],[480,260]],"answer":72}
```

### task_charts__area__interval_area_value / single / answer_only / sample 6451018316265519

- `instance_seed`: `6451018316265519`
- `word_count`: `58`
- `body_word_count`: `43`

```text
The visual shows one filled area chart with labeled x-axis positions and numeric values shown at the points. Compute the area under the area chart from "LIMN" to "LDXC": for each adjacent x-axis pair, average the two point values, then sum those averages.
Answer format: set "answer" to the requested area as an integer.
Example JSON:
{"answer":72}
```

### task_charts__area__stacked_band_dominance_label / single / answer_and_annotation / sample 1607341642743114

- `instance_seed`: `1607341642743114`
- `word_count`: `80`
- `body_word_count`: `34`

```text
The figure shows one stacked area chart with colored category bands, numeric band values, and a legend. Sum each category's band values over "Cope" through "Iro" in displayed x-axis order; which category is largest?
Annotation format: set "annotation" to [x, y] pixel points at the centers of the answer category's band-value points in the queried x-axis interval.
Answer field: set "answer" to the exact category label as a string.
Example JSON:
{"annotation":[[210,420],[330,390],[450,360]],"answer":"Orion"}
```

### task_charts__area__stacked_band_dominance_label / single / answer_only / sample 1607341642743114

- `instance_seed`: `1607341642743114`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The figure shows one stacked area chart with colored category bands, numeric band values, and a legend. Sum each category's band values over "Cope" through "Iro" in displayed x-axis order; which category is largest?
Answer field: set "answer" to the exact category label as a string.
Example JSON:
{"answer":"Orion"}
```

### task_charts__area__stacked_band_interval_sum_value / single / answer_and_annotation / sample 8593850097088174

- `instance_seed`: `8593850097088174`
- `word_count`: `87`
- `body_word_count`: `34`

```text
The image shows one stacked area chart with colored category bands, numeric band values, and a legend. Add the band values for "Tykira" across displayed x-axis labels "Nist" through "Unk"; what is the total?
Annotation format: set "annotation" to [x, y] pixel points at the centers of the queried category's band-value points from the first queried x-axis label through the second queried x-axis label.
Answer field: set "answer" to the requested band-value sum as an integer.
Example JSON:
{"annotation":[[220,380],[330,340],[440,310]],"answer":36}
```

### task_charts__area__stacked_band_interval_sum_value / single / answer_only / sample 8593850097088174

- `instance_seed`: `8593850097088174`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The image shows one stacked area chart with colored category bands, numeric band values, and a legend. Add the band values for "Tykira" across displayed x-axis labels "Nist" through "Unk"; what is the total?
Format for the "answer" field: set "answer" to the requested band-value sum as an integer.
Example JSON:
{"answer":36}
```

### task_charts__bar_3d__category_extremum_gap_value / single / answer_and_annotation / sample 6760369301534112

- `instance_seed`: `6760369301534112`
- `word_count`: `88`
- `body_word_count`: `37`

```text
The figure shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. What is the highest-minus-lowest series value within category "2023"?
Required annotation format: set "annotation" to an object with keys "highest" and "lowest", each mapped to the [x, y] top-center point on the corresponding bar in the requested category.
Required answer format: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"annotation":{"highest":[250,330],"lowest":[210,360]},"answer":18}
```

### task_charts__bar_3d__category_extremum_gap_value / single / answer_only / sample 6760369301534112

- `instance_seed`: `6760369301534112`
- `word_count`: `51`
- `body_word_count`: `37`

```text
The figure shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. What is the highest-minus-lowest series value within category "2023"?
Answer format: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"answer":18}
```

### task_charts__bar_3d__category_threshold_count / single / answer_and_annotation / sample 4561179169611965

- `instance_seed`: `4561179169611965`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For category "2023", how many series have values below 15?
Format for the "annotation" field: set "annotation" to [x, y] pixel points, one at the top-center point on each bar that satisfies the stated condition.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[210,360],[250,330],[290,300]],"answer":3}
```

### task_charts__bar_3d__category_threshold_count / single / answer_only / sample 4561179169611965

- `instance_seed`: `4561179169611965`
- `word_count`: `51`
- `body_word_count`: `38`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For category "2023", how many series have values below 15?
Answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__bar_3d__category_total_gap_value / single / answer_and_annotation / sample 97382142690796

- `instance_seed`: `97382142690796`
- `word_count`: `97`
- `body_word_count`: `42`

```text
The image shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across the two categories "EOG" and "ONB", how far apart are their series totals?
Annotation format: set "annotation" to an object mapping each compared category label to the [x, y] top-center points on all series bars in that category.
Final answer format: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"annotation":{"Banc":[[210,360],[250,330],[290,300]],"Obic":[[430,260],[470,240],[510,220]]},"answer":18}
```

### task_charts__bar_3d__category_total_gap_value / single / answer_only / sample 97382142690796

- `instance_seed`: `97382142690796`
- `word_count`: `56`
- `body_word_count`: `52`

```text
The image shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across the two categories "EOG" and "ONB", how far apart are their series totals?
Answer field: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"answer":18}
```

### task_charts__bar_3d__category_total_value / single / answer_and_annotation / sample 780093757521523

- `instance_seed`: `780093757521523`
- `word_count`: `83`
- `body_word_count`: `38`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For category "2024", compute the sum over all colored series.
Annotation format: set "annotation" to [x, y] pixel points, one at the top-center point on each relevant bar included in the requested category total.
Final answer format: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[210,360],[250,330],[290,300]],"answer":72}
```

### task_charts__bar_3d__category_total_value / single / answer_only / sample 780093757521523

- `instance_seed`: `780093757521523`
- `word_count`: `51`
- `body_word_count`: `38`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For category "2024", compute the sum over all colored series.
Answer format: set "answer" to the requested integer total.
Example JSON:
{"answer":72}
```

### task_charts__bar_3d__pairwise_comparison_count / single / answer_and_annotation / sample 8494785466052992

- `instance_seed`: `8494785466052992`
- `word_count`: `115`
- `body_word_count`: `46`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For the pair "Spargur" and "Tracey", how many displayed categories have the first series higher than the second?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the top-center point on the first series bar and the top-center point on the second series bar for one counted category; use [] if no categories match.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[210,360],[210,260]],[[320,330],[320,240]],[[430,300],[430,220]]],"answer":3}
```

### task_charts__bar_3d__pairwise_comparison_count / single / answer_only / sample 8494785466052992

- `instance_seed`: `8494785466052992`
- `word_count`: `60`
- `body_word_count`: `46`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. For the pair "Spargur" and "Tracey", how many displayed categories have the first series higher than the second?
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__bar_3d__series_category_scope_total_value / series_interval_total_value / answer_and_annotation / sample 8850366164105841

- `instance_seed`: `8850366164105841`
- `word_count`: `83`
- `body_word_count`: `39`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Find series "Ottmar" and sum its bars from "SHBI" through "PROP".
Annotation format: set "annotation" to [x, y] pixel points, one at the top-center point on each relevant bar included in the requested interval total.
Answer format: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[210,360],[320,330],[430,300]],"answer":72}
```

### task_charts__bar_3d__series_category_scope_total_value / series_interval_total_value / answer_only / sample 8850366164105841

- `instance_seed`: `8850366164105841`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Find series "Ottmar" and sum its bars from "SHBI" through "PROP".
Answer field: set "answer" to the requested integer total.
Example JSON:
{"answer":72}
```

### task_charts__bar_3d__series_category_scope_total_value / series_total_value / answer_and_annotation / sample 5537563464061729

- `instance_seed`: `5537563464061729`
- `word_count`: `88`
- `body_word_count`: `42`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across all category labels, what is the sum of the bars for series "Mekeba"?
Required annotation format: set "annotation" to [x, y] pixel points, one at the top-center point on each relevant bar included in the requested series total.
Required answer format: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[210,360],[320,330],[430,300]],"answer":72}
```

### task_charts__bar_3d__series_category_scope_total_value / series_total_value / answer_only / sample 5537563464061729

- `instance_seed`: `5537563464061729`
- `word_count`: `55`
- `body_word_count`: `42`

```text
The panel shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across all category labels, what is the sum of the bars for series "Mekeba"?
Answer format: set "answer" to the requested integer total.
Example JSON:
{"answer":72}
```

### task_charts__bar_3d__series_threshold_count / single / answer_and_annotation / sample 8562638351245489

- `instance_seed`: `8562638351245489`
- `word_count`: `84`
- `body_word_count`: `42`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Looking across categories for series "Fiji", count the bars with values at least 8.
Annotation format: set "annotation" to [x, y] pixel points, one at the top-center point on each bar that satisfies the stated condition.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[210,360],[320,330],[430,300]],"answer":3}
```

### task_charts__bar_3d__series_threshold_count / single / answer_only / sample 8562638351245489

- `instance_seed`: `8562638351245489`
- `word_count`: `55`
- `body_word_count`: `42`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Looking across categories for series "Fiji", count the bars with values at least 8.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__bar_3d__series_total_gap_value / single / answer_and_annotation / sample 5054212823624086

- `instance_seed`: `5054212823624086`
- `word_count`: `96`
- `body_word_count`: `41`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across all categories, how far apart are the totals for "Stone" and "Pro"?
Annotation format: set "annotation" to an object mapping each compared series label to the [x, y] top-center points on that series' bars across the displayed categories.
Answer field: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"annotation":{"Bambari":[[210,360],[320,330],[430,300]],"Lascano":[[250,340],[360,310],[470,280]]},"answer":18}
```

### task_charts__bar_3d__series_total_gap_value / single / answer_only / sample 5054212823624086

- `instance_seed`: `5054212823624086`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The chart shows one perspective 3D bar chart with category labels on the front axis, colored series labels in the legend, and integer value labels on the bars. Across all categories, how far apart are the totals for "Stone" and "Pro"?
Answer field: set "answer" to the requested nonnegative integer difference.
Example JSON:
{"answer":18}
```

### task_charts__boxplot__iqr_extremum_label / largest_iqr_label / answer_and_annotation / sample 8448488423927792

- `instance_seed`: `8448488423927792`
- `word_count`: `79`
- `body_word_count`: `39`

```text
The visual shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Which label has the largest interquartile range?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the winning boxplot's interquartile-range rectangle.
Answer field: set "answer" to the exact visible boxplot label as a string.
Example JSON:
{"annotation":[394,210,466,290],"answer":"Ivory"}
```

### task_charts__boxplot__iqr_extremum_label / largest_iqr_label / answer_only / sample 8448488423927792

- `instance_seed`: `8448488423927792`
- `word_count`: `56`
- `body_word_count`: `39`

```text
The visual shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Which label has the largest interquartile range?
Answer format: set "answer" to the exact visible boxplot label as a string.
Example JSON:
{"answer":"Ivory"}
```

### task_charts__boxplot__iqr_extremum_label / smallest_iqr_label / answer_and_annotation / sample 974010406852760

- `instance_seed`: `974010406852760`
- `word_count`: `79`
- `body_word_count`: `39`

```text
The chart shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Which label has the smallest interquartile range?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the winning boxplot's interquartile-range rectangle.
Answer field: set "answer" to the exact visible boxplot label as a string.
Example JSON:
{"annotation":[394,210,466,290],"answer":"Ivory"}
```

### task_charts__boxplot__iqr_extremum_label / smallest_iqr_label / answer_only / sample 974010406852760

- `instance_seed`: `974010406852760`
- `word_count`: `56`
- `body_word_count`: `52`

```text
The chart shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Which label has the smallest interquartile range?
Answer field: set "answer" to the exact visible boxplot label as a string.
Example JSON:
{"answer":"Ivory"}
```

### task_charts__boxplot__median_rank_difference_value / median_top_bottom_difference_value / answer_and_annotation / sample 584860001357969

- `instance_seed`: `584860001357969`
- `word_count`: `92`
- `body_word_count`: `45`

```text
The image shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Find the median value gap between the top-ranked boxplot and the bottom-ranked boxplot.
Annotation format: set "annotation" to an object with keys "highest_median_boxplot" and "lowest_median_boxplot", each mapped to an [x,y] pixel center point of that boxplot.
Final answer format: set "answer" to the median difference as an integer.
Example JSON:
{"annotation":{"highest_median_boxplot":[240,300],"lowest_median_boxplot":[430,250]},"answer":14}
```

### task_charts__boxplot__median_rank_difference_value / median_top_bottom_difference_value / answer_only / sample 584860001357969

- `instance_seed`: `584860001357969`
- `word_count`: `63`
- `body_word_count`: `45`

```text
The image shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Find the median value gap between the top-ranked boxplot and the bottom-ranked boxplot.
Format for the "answer" field: set "answer" to the median difference as an integer.
Example JSON:
{"answer":14}
```

### task_charts__boxplot__median_rank_difference_value / median_top_second_difference_value / answer_and_annotation / sample 7481107052478121

- `instance_seed`: `7481107052478121`
- `word_count`: `97`
- `body_word_count`: `45`

```text
The figure shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Find the median value gap between the top-ranked boxplot and the second-ranked boxplot.
Format for the "annotation" field: set "annotation" to an object with keys "highest_median_boxplot" and "second_highest_median_boxplot", each mapped to an [x,y] pixel center point of that boxplot.
Format for the "answer" field: set "answer" to the median difference as an integer.
Example JSON:
{"annotation":{"highest_median_boxplot":[240,300],"second_highest_median_boxplot":[430,250]},"answer":7}
```

### task_charts__boxplot__median_rank_difference_value / median_top_second_difference_value / answer_only / sample 7481107052478121

- `instance_seed`: `7481107052478121`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The figure shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Find the median value gap between the top-ranked boxplot and the second-ranked boxplot.
Answer field: set "answer" to the median difference as an integer.
Example JSON:
{"answer":7}
```

### task_charts__boxplot__median_rank_difference_value / median_top_third_difference_value / answer_and_annotation / sample 1172183138429268

- `instance_seed`: `1172183138429268`
- `word_count`: `93`
- `body_word_count`: `45`

```text
The panel shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Subtract the third-highest median from the highest median. What value do you get?
Required annotation format: set "annotation" to an object with keys "highest_median_boxplot" and "third_highest_median_boxplot", each mapped to an [x,y] pixel center point of that boxplot.
Required answer format: set "answer" to the median difference as an integer.
Example JSON:
{"annotation":{"highest_median_boxplot":[240,300],"third_highest_median_boxplot":[430,250]},"answer":9}
```

### task_charts__boxplot__median_rank_difference_value / median_top_third_difference_value / answer_only / sample 1172183138429268

- `instance_seed`: `1172183138429268`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The panel shows a set of labeled boxplots. Each box spans the interquartile range, the line inside the box marks the median, and the whiskers show the minimum and maximum values shown. Subtract the third-highest median from the highest median. What value do you get?
Answer field: set "answer" to the median difference as an integer.
Example JSON:
{"answer":9}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_absolute_change_label / answer_and_annotation / sample 8088846535680296

- `instance_seed`: `8088846535680296`
- `word_count`: `95`
- `body_word_count`: `35`

```text
The chart shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Which matched label has the largest absolute difference between its Before and After medians?
Format for the "annotation" field: set "annotation" to an object with keys "before_boxplot" and "after_boxplot", each mapped to the [x,y] pixel center point of that winning label's boxplot in the corresponding panel.
Format for the "answer" field: set "answer" to the exact visible matched label as a string.
Example JSON:
{"annotation":{"before_boxplot":[240,300],"after_boxplot":[305,250]},"answer":"Maple"}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_absolute_change_label / answer_only / sample 8088846535680296

- `instance_seed`: `8088846535680296`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The chart shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Which matched label has the largest absolute difference between its Before and After medians?
Answer format: set "answer" to the exact visible matched label as a string.
Example JSON:
{"answer":"Maple"}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_decrease_label / answer_and_annotation / sample 171679461402322

- `instance_seed`: `171679461402322`
- `word_count`: `94`
- `body_word_count`: `34`

```text
The image shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Which matched label shows the largest downward median shift from Before to After?
Format for the "annotation" field: set "annotation" to an object with keys "before_boxplot" and "after_boxplot", each mapped to the [x,y] pixel center point of that winning label's boxplot in the corresponding panel.
Format for the "answer" field: set "answer" to the exact visible matched label as a string.
Example JSON:
{"annotation":{"before_boxplot":[240,250],"after_boxplot":[305,310]},"answer":"Maple"}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_decrease_label / answer_only / sample 171679461402322

- `instance_seed`: `171679461402322`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The image shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Which matched label shows the largest downward median shift from Before to After?
Answer field: set "answer" to the exact visible matched label as a string.
Example JSON:
{"answer":"Maple"}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_increase_label / answer_and_annotation / sample 5223323281178273

- `instance_seed`: `5223323281178273`
- `word_count`: `89`
- `body_word_count`: `35`

```text
The chart shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Using After minus Before for each label, which label has the largest median increase?
Annotation format: set "annotation" to an object with keys "before_boxplot" and "after_boxplot", each mapped to the [x,y] pixel center point of that winning label's boxplot in the corresponding panel.
Answer format: set "answer" to the exact visible matched label as a string.
Example JSON:
{"annotation":{"before_boxplot":[240,300],"after_boxplot":[305,250]},"answer":"Maple"}
```

### task_charts__boxplot__paired_median_shift_label / paired_median_greatest_increase_label / answer_only / sample 5223323281178273

- `instance_seed`: `5223323281178273`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The chart shows two side-by-side boxplot panels with matching labels. The left panel is Before and the right panel is After. Using After minus Before for each label, which label has the largest median increase?
Answer field: set "answer" to the exact visible matched label as a string.
Example JSON:
{"answer":"Maple"}
```

### task_charts__candlestick__counterfactual_close_value / close_after_body_decrease_value / answer_and_annotation / sample 1131177560339701

- `instance_seed`: `1131177560339701`
- `word_count`: `91`
- `body_word_count`: `51`

```text
The visual shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. For candle "Gold", leave the open value fixed, preserve direction, and decrease the open-close body size by 2 units. What is the resulting close value?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point at the center of the target candle body.
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"annotation":[262,280],"answer":42}
```

### task_charts__candlestick__counterfactual_close_value / close_after_body_decrease_value / answer_only / sample 1131177560339701

- `instance_seed`: `1131177560339701`
- `word_count`: `64`
- `body_word_count`: `51`

```text
The visual shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. For candle "Gold", leave the open value fixed, preserve direction, and decrease the open-close body size by 2 units. What is the resulting close value?
Answer format: set "answer" to the requested integer value.
Example JSON:
{"answer":42}
```

### task_charts__candlestick__counterfactual_close_value / close_after_body_increase_value / answer_and_annotation / sample 5330121906552802

- `instance_seed`: `5330121906552802`
- `word_count`: `87`
- `body_word_count`: `52`

```text
The figure shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Using period "Rome", keep the open value fixed and increase only the open-close body size by 5 units while preserving direction. What is the new close?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the target candle body.
Final answer format: set "answer" to the requested integer value.
Example JSON:
{"annotation":[262,280],"answer":42}
```

### task_charts__candlestick__counterfactual_close_value / close_after_body_increase_value / answer_only / sample 5330121906552802

- `instance_seed`: `5330121906552802`
- `word_count`: `65`
- `body_word_count`: `61`

```text
The figure shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Using period "Rome", keep the open value fixed and increase only the open-close body size by 5 units while preserving direction. What is the new close?
Answer field: set "answer" to the requested integer value.
Example JSON:
{"answer":42}
```

### task_charts__candlestick__range_extremum_label / largest_body_range_label / answer_and_annotation / sample 3800120279959764

- `instance_seed`: `3800120279959764`
- `word_count`: `83`
- `body_word_count`: `42`

```text
The image shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Compare the absolute close-open body sizes for all candles. Which label has the largest body size?
Annotation format: set "annotation" to one segment [[x1,y1],[x2,y2]] running vertically through the answer candle's open-close body.
Final answer format: set "answer" to the exact period label as a string.
Example JSON:
{"annotation":[[542,238],[542,314]],"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / largest_body_range_label / answer_only / sample 3800120279959764

- `instance_seed`: `3800120279959764`
- `word_count`: `61`
- `body_word_count`: `42`

```text
The image shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Compare the absolute close-open body sizes for all candles. Which label has the largest body size?
Format for the "answer" field: set "answer" to the exact period label as a string.
Example JSON:
{"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / largest_wick_range_label / answer_and_annotation / sample 2306972685328251

- `instance_seed`: `2306972685328251`
- `word_count`: `74`
- `body_word_count`: `34`

```text
The chart shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Which period has the largest high-low wick range?
Annotation format: set "annotation" to one segment [[x1,y1],[x2,y2]] running along the answer candle's high-low wick line.
Answer field: set "answer" to the exact period label as a string.
Example JSON:
{"annotation":[[542,210],[542,342]],"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / largest_wick_range_label / answer_only / sample 2306972685328251

- `instance_seed`: `2306972685328251`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The chart shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Which period has the largest high-low wick range?
Format for the "answer" field: set "answer" to the exact period label as a string.
Example JSON:
{"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / smallest_body_range_label / answer_and_annotation / sample 4802237400389532

- `instance_seed`: `4802237400389532`
- `word_count`: `82`
- `body_word_count`: `42`

```text
The figure shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Compare the absolute close-open body sizes for all candles. Which label has the smallest body size?
Annotation format: set "annotation" to one segment [[x1,y1],[x2,y2]] running vertically through the answer candle's open-close body.
Answer format: set "answer" to the exact period label as a string.
Example JSON:
{"annotation":[[542,238],[542,314]],"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / smallest_body_range_label / answer_only / sample 4802237400389532

- `instance_seed`: `4802237400389532`
- `word_count`: `59`
- `body_word_count`: `42`

```text
The figure shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. Compare the absolute close-open body sizes for all candles. Which label has the smallest body size?
Final answer format: set "answer" to the exact period label as a string.
Example JSON:
{"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / smallest_wick_range_label / answer_and_annotation / sample 2749656417484743

- `instance_seed`: `2749656417484743`
- `word_count`: `78`
- `body_word_count`: `36`

```text
The panel shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. What period label corresponds to the smallest high-low wick range?
Required annotation format: set "annotation" to one segment [[x1,y1],[x2,y2]] running along the answer candle's high-low wick line.
Required answer format: set "answer" to the exact period label as a string.
Example JSON:
{"annotation":[[542,210],[542,342]],"answer":"K4"}
```

### task_charts__candlestick__range_extremum_label / smallest_wick_range_label / answer_only / sample 2749656417484743

- `instance_seed`: `2749656417484743`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The panel shows a candlestick OHLC chart with labeled periods. Each candle has printed O, H, L, and C values for open, high, low, and close. What period label corresponds to the smallest high-low wick range?
Required answer format: set "answer" to the exact period label as a string.
Example JSON:
{"answer":"K4"}
```

### task_charts__combo_mark__absolute_gap_extremum_label / largest_absolute_gap_label / answer_and_annotation / sample 6068341470936668

- `instance_seed`: `6068341470936668`
- `word_count`: `106`
- `body_word_count`: `37`

```text
The image shows a combo chart where the filled area shows "Bronze", and the overlaid line shows "Comet". Each category has printed values for both series. Find the category where the two series values are farthest apart.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__absolute_gap_extremum_label / largest_absolute_gap_label / answer_only / sample 6068341470936668

- `instance_seed`: `6068341470936668`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The image shows a combo chart where the filled area shows "Bronze", and the overlaid line shows "Comet". Each category has printed values for both series. Find the category where the two series values are farthest apart.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__absolute_gap_extremum_label / smallest_nonzero_absolute_gap_label / answer_and_annotation / sample 1105819069109579

- `instance_seed`: `1105819069109579`
- `word_count`: `116`
- `body_word_count`: `47`

```text
The image shows a combo chart where vertical bars show "Quartz" on the left axis and the overlaid line shows "Valley" on the right axis. Each category has printed values for both series. Find the category where the two series values differ by the smallest nonzero amount.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__absolute_gap_extremum_label / smallest_nonzero_absolute_gap_label / answer_only / sample 1105819069109579

- `instance_seed`: `1105819069109579`
- `word_count`: `64`
- `body_word_count`: `47`

```text
The image shows a combo chart where vertical bars show "Quartz" on the left axis and the overlaid line shows "Valley" on the right axis. Each category has printed values for both series. Find the category where the two series values differ by the smallest nonzero amount.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_line_extremum_label / max_line_where_primary_above_threshold / answer_and_annotation / sample 8023167637589174

- `instance_seed`: `8023167637589174`
- `word_count`: `118`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Tickets" on the left axis and the overlaid line shows "Apparel" on the right axis. Each category has printed values for both series. Among categories where "Tickets" is above 39, which category has the highest "Apparel" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_line_extremum_label / max_line_where_primary_above_threshold / answer_only / sample 8023167637589174

- `instance_seed`: `8023167637589174`
- `word_count`: `65`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Tickets" on the left axis and the overlaid line shows "Apparel" on the right axis. Each category has printed values for both series. Among categories where "Tickets" is above 39, which category has the highest "Apparel" line value?
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_line_extremum_label / min_line_where_primary_above_threshold / answer_and_annotation / sample 8442721128581216

- `instance_seed`: `8442721128581216`
- `word_count`: `118`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Support" on the left axis and the overlaid line shows "Devices" on the right axis. Each category has printed values for both series. Among categories where "Support" is above 70, which category has the lowest "Devices" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_line_extremum_label / min_line_where_primary_above_threshold / answer_only / sample 8442721128581216

- `instance_seed`: `8442721128581216`
- `word_count`: `65`
- `body_word_count`: `48`

```text
The image shows a combo chart where vertical bars show "Support" on the left axis and the overlaid line shows "Devices" on the right axis. Each category has printed values for both series. Among categories where "Support" is above 70, which category has the lowest "Devices" line value?
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_primary_extremum_label / max_primary_where_line_below_threshold / answer_and_annotation / sample 1637473416246127

- `instance_seed`: `1637473416246127`
- `word_count`: `104`
- `body_word_count`: `35`

```text
The figure shows a bar-and-line combo chart: bars encode "Slate", and the overlaid line encodes "Nova" on the same value scale. Among categories where "Nova" is below 75, which category has the highest "Slate" value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_primary_extremum_label / max_primary_where_line_below_threshold / answer_only / sample 1637473416246127

- `instance_seed`: `1637473416246127`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The figure shows a bar-and-line combo chart: bars encode "Slate", and the overlaid line encodes "Nova" on the same value scale. Among categories where "Nova" is below 75, which category has the highest "Slate" value?
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_primary_extremum_label / min_primary_where_line_below_threshold / answer_and_annotation / sample 8992111285610397

- `instance_seed`: `8992111285610397`
- `word_count`: `114`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "River" and the overlaid line shows "Beacon" on the same value axis. Each category has printed values for both series. Among categories where "Beacon" is below 33, which category has the lowest "River" value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__conditioned_primary_extremum_label / min_primary_where_line_below_threshold / answer_only / sample 8992111285610397

- `instance_seed`: `8992111285610397`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "River" and the overlaid line shows "Beacon" on the same value axis. Each category has printed values for both series. Among categories where "Beacon" is below 33, which category has the lowest "River" value?
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__cross_mark_difference_value / line_minus_primary_at_label / answer_and_annotation / sample 7922823628437837

- `instance_seed`: `7922823628437837`
- `word_count`: `99`
- `body_word_count`: `32`

```text
The figure shows a bar-and-line combo chart: bars encode "Comet", and the overlaid line encodes "Atlas" on the same value scale. For "KK7", subtract the "Comet" value from the "Atlas" line value.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the queried category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same category.
Answer format: set "answer" to the requested signed difference as an integer.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":-12}
```

### task_charts__combo_mark__cross_mark_difference_value / line_minus_primary_at_label / answer_only / sample 7922823628437837

- `instance_seed`: `7922823628437837`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The figure shows a bar-and-line combo chart: bars encode "Comet", and the overlaid line encodes "Atlas" on the same value scale. For "KK7", subtract the "Comet" value from the "Atlas" line value.
Final answer format: set "answer" to the requested signed difference as an integer.
Example JSON:
{"answer":-12}
```

### task_charts__combo_mark__cross_mark_difference_value / primary_minus_line_at_label / answer_and_annotation / sample 6678089473717765

- `instance_seed`: `6678089473717765`
- `word_count`: `110`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Media" and the overlaid line shows "Bakery" on the same value axis. Each category has printed values for both series. At category "ZW7", what is the "Media" value minus the "Bakery" line value?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the queried category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same category.
Answer format: set "answer" to the requested signed difference as an integer.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":12}
```

### task_charts__combo_mark__cross_mark_difference_value / primary_minus_line_at_label / answer_only / sample 6678089473717765

- `instance_seed`: `6678089473717765`
- `word_count`: `59`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Media" and the overlaid line shows "Bakery" on the same value axis. Each category has printed values for both series. At category "ZW7", what is the "Media" value minus the "Bakery" line value?
Answer format: set "answer" to the requested signed difference as an integer.
Example JSON:
{"answer":12}
```

### task_charts__combo_mark__directional_gap_extremum_label / largest_line_over_primary_gap_label / answer_and_annotation / sample 1859135762442502

- `instance_seed`: `1859135762442502`
- `word_count`: `109`
- `body_word_count`: `39`

```text
The image shows a combo chart where each stacked bar's printed total shows "Grocery", and the overlaid line shows "Telecom". Each category has printed values for both series. Find the category where "Telecom" exceeds "Grocery" by the largest amount.
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__directional_gap_extremum_label / largest_line_over_primary_gap_label / answer_only / sample 1859135762442502

- `instance_seed`: `1859135762442502`
- `word_count`: `56`
- `body_word_count`: `39`

```text
The image shows a combo chart where each stacked bar's printed total shows "Grocery", and the overlaid line shows "Telecom". Each category has printed values for both series. Find the category where "Telecom" exceeds "Grocery" by the largest amount.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__directional_gap_extremum_label / largest_primary_over_line_gap_label / answer_and_annotation / sample 6934222898042463

- `instance_seed`: `6934222898042463`
- `word_count`: `112`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Pearl" and the overlaid line shows "Valley" on the same value axis. Each category has printed values for both series. Which category has the largest positive gap where "Pearl" is greater than "Valley"?
Annotation format: set "annotation" to an object with keys "primary_mark" and "line_mark"; "primary_mark" is a [x,y] pixel point on the primary-series mark at the answer category, and "line_mark" is a [x,y] pixel point on the overlaid line mark at the same answer category.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":{"primary_mark":[180,260],"line_mark":[180,190]},"answer":"Cedar"}
```

### task_charts__combo_mark__directional_gap_extremum_label / largest_primary_over_line_gap_label / answer_only / sample 6934222898042463

- `instance_seed`: `6934222898042463`
- `word_count`: `60`
- `body_word_count`: `43`

```text
The image shows a combo chart where vertical bars show "Pearl" and the overlaid line shows "Valley" on the same value axis. Each category has printed values for both series. Which category has the largest positive gap where "Pearl" is greater than "Valley"?
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_above_and_line_above / answer_and_annotation / sample 8474227367835465

- `instance_seed`: `8474227367835465`
- `word_count`: `94`
- `body_word_count`: `31`

```text
The figure shows stacked bars for "Crimson" with an overlaid line for "Teal"; each category displays the relevant printed values. How many categories have "Crimson" above 60 and "Teal" above 42?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the primary-series mark point and the overlaid line mark point for one matching category; use [] if no categories match.
Final answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"annotation":[[[180,260],[180,190]],[[360,220],[360,170]]],"answer":2}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_above_and_line_above / answer_only / sample 8474227367835465

- `instance_seed`: `8474227367835465`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The figure shows stacked bars for "Crimson" with an overlaid line for "Teal"; each category displays the relevant printed values. How many categories have "Crimson" above 60 and "Teal" above 42?
Final answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"answer":2}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_above_and_line_below / answer_and_annotation / sample 7342920740193949

- `instance_seed`: `7342920740193949`
- `word_count`: `106`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "Travel" on the left axis and the overlaid line shows "Devices" on the right axis. Each category has printed values for both series. How many categories have "Travel" above 61 and "Devices" below 61?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the primary-series mark point and the overlaid line mark point for one matching category; use [] if no categories match.
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"annotation":[[[180,260],[180,190]],[[360,220],[360,170]]],"answer":2}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_above_and_line_below / answer_only / sample 7342920740193949

- `instance_seed`: `7342920740193949`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "Travel" on the left axis and the overlaid line shows "Devices" on the right axis. Each category has printed values for both series. How many categories have "Travel" above 61 and "Devices" below 61?
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"answer":2}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_below_and_line_above / answer_and_annotation / sample 2913141561169422

- `instance_seed`: `2913141561169422`
- `word_count`: `100`
- `body_word_count`: `37`

```text
The image shows a combo chart where the filled area shows "Media", and the overlaid line shows "Sports". Each category has printed values for both series. How many categories have "Media" below 66 and "Sports" above 49?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the primary-series mark point and the overlaid line mark point for one matching category; use [] if no categories match.
Final answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"annotation":[[[180,260],[180,190]],[[360,220],[360,170]]],"answer":2}
```

### task_charts__combo_mark__dual_threshold_condition_count / primary_below_and_line_above / answer_only / sample 2913141561169422

- `instance_seed`: `2913141561169422`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The image shows a combo chart where the filled area shows "Media", and the overlaid line shows "Sports". Each category has printed values for both series. How many categories have "Media" below 66 and "Sports" above 49?
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"answer":2}
```

### task_charts__combo_mark__interval_threshold_condition_count / line_between_and_primary_above / answer_and_annotation / sample 447995377914263

- `instance_seed`: `447995377914263`
- `word_count`: `94`
- `body_word_count`: `32`

```text
The figure shows a dual-axis bar-and-line combo chart: bars encode "Flint", and the overlaid line encodes "Grove". How many categories have "Grove" between 20 and 35, inclusive, while "Flint" is above 43?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the primary-series mark point and the overlaid line mark point for one matching category; use [] if no categories match.
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"annotation":[[[180,260],[180,190]],[[360,220],[360,170]]],"answer":2}
```

### task_charts__combo_mark__interval_threshold_condition_count / line_between_and_primary_above / answer_only / sample 447995377914263

- `instance_seed`: `447995377914263`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The figure shows a dual-axis bar-and-line combo chart: bars encode "Flint", and the overlaid line encodes "Grove". How many categories have "Grove" between 20 and 35, inclusive, while "Flint" is above 43?
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"answer":2}
```

### task_charts__combo_mark__interval_threshold_condition_count / primary_between_and_line_above / answer_and_annotation / sample 1479391059472675

- `instance_seed`: `1479391059472675`
- `word_count`: `106`
- `body_word_count`: `44`

```text
The image shows a combo chart where each stacked bar's printed total shows "Harbor", and the overlaid line shows "Comet". Each category has printed values for both series. Count categories where "Harbor" is in the inclusive range 54 to 77 and "Comet" exceeds 56.
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the primary-series mark point and the overlaid line mark point for one matching category; use [] if no categories match.
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"annotation":[[[180,260],[180,190]],[[360,220],[360,170]]],"answer":2}
```

### task_charts__combo_mark__interval_threshold_condition_count / primary_between_and_line_above / answer_only / sample 1479391059472675

- `instance_seed`: `1479391059472675`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The image shows a combo chart where each stacked bar's printed total shows "Harbor", and the overlaid line shows "Comet". Each category has printed values for both series. Count categories where "Harbor" is in the inclusive range 54 to 77 and "Comet" exceeds 56.
Answer format: set "answer" to the number of matching categories as an integer.
Example JSON:
{"answer":2}
```

### task_charts__combo_mark__series_threshold_crossing_label / line_first_above_threshold_label / answer_and_annotation / sample 7847423086119652

- `instance_seed`: `7847423086119652`
- `word_count`: `80`
- `body_word_count`: `42`

```text
The image shows a combo chart where each stacked bar's printed total shows "Ruby", and the overlaid line shows "River". Each category has printed values for both series. Reading left to right, what is the first category where "River" is above 74?
Annotation format: set "annotation" to one [x,y] pixel point on the target-series mark at the answer category.
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"annotation":[400,240],"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / line_first_above_threshold_label / answer_only / sample 7847423086119652

- `instance_seed`: `7847423086119652`
- `word_count`: `59`
- `body_word_count`: `42`

```text
The image shows a combo chart where each stacked bar's printed total shows "Ruby", and the overlaid line shows "River". Each category has printed values for both series. Reading left to right, what is the first category where "River" is above 74?
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / line_first_below_threshold_label / answer_and_annotation / sample 7111007993356273

- `instance_seed`: `7111007993356273`
- `word_count`: `80`
- `body_word_count`: `42`

```text
The image shows a combo chart where the filled area shows "Delta", and the overlaid line shows "Jade". Each category has printed values for both series. Scan categories from left to right and identify the first label where "Jade" is below 82.
Annotation format: set "annotation" to one [x,y] pixel point on the target-series mark at the answer category.
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"annotation":[400,240],"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / line_first_below_threshold_label / answer_only / sample 7111007993356273

- `instance_seed`: `7111007993356273`
- `word_count`: `60`
- `body_word_count`: `42`

```text
The image shows a combo chart where the filled area shows "Delta", and the overlaid line shows "Jade". Each category has printed values for both series. Scan categories from left to right and identify the first label where "Jade" is below 82.
Final answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / primary_first_above_threshold_label / answer_and_annotation / sample 1471370712399924

- `instance_seed`: `1471370712399924`
- `word_count`: `85`
- `body_word_count`: `47`

```text
The image shows a combo chart where vertical bars show "Dining" on the left axis and the overlaid line shows "Kitchen" on the right axis. Each category has printed values for both series. Reading left to right, what is the first category where "Dining" is above 13?
Annotation format: set "annotation" to one [x,y] pixel point on the target-series mark at the answer category.
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"annotation":[400,240],"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / primary_first_above_threshold_label / answer_only / sample 1471370712399924

- `instance_seed`: `1471370712399924`
- `word_count`: `64`
- `body_word_count`: `47`

```text
The image shows a combo chart where vertical bars show "Dining" on the left axis and the overlaid line shows "Kitchen" on the right axis. Each category has printed values for both series. Reading left to right, what is the first category where "Dining" is above 13?
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / primary_first_below_threshold_label / answer_and_annotation / sample 4087062344678565

- `instance_seed`: `4087062344678565`
- `word_count`: `82`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "Grocery" and the overlaid line shows "Apparel" on the same value axis. Each category has printed values for both series. Reading left to right, what is the first category where "Grocery" is below 52?
Annotation format: set "annotation" to one [x,y] pixel point on the target-series mark at the answer category.
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"annotation":[400,240],"answer":"Harbor"}
```

### task_charts__combo_mark__series_threshold_crossing_label / primary_first_below_threshold_label / answer_only / sample 4087062344678565

- `instance_seed`: `4087062344678565`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The image shows a combo chart where vertical bars show "Grocery" and the overlaid line shows "Apparel" on the same value axis. Each category has printed values for both series. Reading left to right, what is the first category where "Grocery" is below 52?
Answer format: set "answer" to the first matching category label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__composition_shift_l1_distance / single / answer_and_annotation / sample 3580409730750447

- `instance_seed`: `3580409730750447`
- `word_count`: `92`
- `body_word_count`: `44`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Compare panel "Valley" with panel "Hazel". Add the absolute percentage-point differences for every segment. What is the total?
Annotation format: set "annotation" to an array of two [x0,y0,x1,y1] pixel boxes around the full compared panels.
Answer format: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"annotation":[[120,90,380,520],[460,90,720,520]],"answer":28}
```

### task_charts__composition_panels__composition_shift_l1_distance / single / answer_only / sample 3580409730750447

- `instance_seed`: `3580409730750447`
- `word_count`: `66`
- `body_word_count`: `44`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Compare panel "Valley" with panel "Hazel". Add the absolute percentage-point differences for every segment. What is the total?
Format for the "answer" field: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"answer":28}
```

### task_charts__composition_panels__conditioned_panel_sum_from_percent / single / answer_and_annotation / sample 7372415142153742

- `instance_seed`: `7372415142153742`
- `word_count`: `96`
- `body_word_count`: `44`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. For the panels with Segment "Nimbus" more than 38%, add the Segment "Delta" counts. What is the total?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full panels included in the sum.
Required answer format: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"annotation":[[120,90,380,520],[460,90,720,520]],"answer":720}
```

### task_charts__composition_panels__conditioned_panel_sum_from_percent / single / answer_only / sample 7372415142153742

- `instance_seed`: `7372415142153742`
- `word_count`: `63`
- `body_word_count`: `44`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. For the panels with Segment "Nimbus" more than 38%, add the Segment "Delta" counts. What is the total?
Answer format: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"answer":720}
```

### task_charts__composition_panels__segment_count_extremum_panel_label / largest_count / answer_and_annotation / sample 7940607805681920

- `instance_seed`: `7940607805681920`
- `word_count`: `92`
- `body_word_count`: `38`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Compute the Segment "Health" count in each panel. Which panel is largest?
Required annotation format: set "annotation" to an object with keys "segment_percent" and "panel_total"; put [x,y] pixel points on the answer panel's Segment "Health" percentage label and total-count text.
Required answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":{"segment_percent":[260,310],"panel_total":[245,110]},"answer":"Harbor"}
```

### task_charts__composition_panels__segment_count_extremum_panel_label / largest_count / answer_only / sample 7940607805681920

- `instance_seed`: `7940607805681920`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Compute the Segment "Health" count in each panel. Which panel is largest?
Answer field: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__segment_count_extremum_panel_label / smallest_count / answer_and_annotation / sample 2443261944111903

- `instance_seed`: `2443261944111903`
- `word_count`: `91`
- `body_word_count`: `38`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Looking across all panels, which panel has the smallest Segment "Travel" count?
Annotation format: set "annotation" to an object with keys "segment_percent" and "panel_total"; put [x,y] pixel points on the answer panel's Segment "Travel" percentage label and total-count text.
Final answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":{"segment_percent":[260,310],"panel_total":[245,110]},"answer":"Harbor"}
```

### task_charts__composition_panels__segment_count_extremum_panel_label / smallest_count / answer_only / sample 2443261944111903

- `instance_seed`: `2443261944111903`
- `word_count`: `58`
- `body_word_count`: `38`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Looking across all panels, which panel has the smallest Segment "Travel" count?
Format for the "answer" field: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__segment_count_nearest_target_panel_label / single / answer_and_annotation / sample 3424633877621807

- `instance_seed`: `3424633877621807`
- `word_count`: `79`
- `body_word_count`: `39`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Using counts, not percentages, which panel's Segment "Indigo" count is closest to 780?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full answer panel.
Final answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":[120,90,380,520],"answer":"Harbor"}
```

### task_charts__composition_panels__segment_count_nearest_target_panel_label / single / answer_only / sample 3424633877621807

- `instance_seed`: `3424633877621807`
- `word_count`: `56`
- `body_word_count`: `39`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Using counts, not percentages, which panel's Segment "Indigo" count is closest to 780?
Answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label / largest_count_gap / answer_and_annotation / sample 7152289703067321

- `instance_seed`: `7152289703067321`
- `word_count`: `85`
- `body_word_count`: `44`

```text
The image shows several small pie charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Across all panels, find the largest count gap between Segment "Azure" and Segment "Indigo". Which panel is it?
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full answer panel.
Required answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":[120,90,380,520],"answer":"Harbor"}
```

### task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label / largest_count_gap / answer_only / sample 7152289703067321

- `instance_seed`: `7152289703067321`
- `word_count`: `61`
- `body_word_count`: `57`

```text
The image shows several small pie charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Across all panels, find the largest count gap between Segment "Azure" and Segment "Indigo". Which panel is it?
Answer field: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label / smallest_count_gap / answer_and_annotation / sample 5081827815877320

- `instance_seed`: `5081827815877320`
- `word_count`: `84`
- `body_word_count`: `45`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. For each panel, compute the count gap between Segment "Supplies" and Segment "Beauty". Which panel has the smallest gap?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full answer panel.
Answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":[120,90,380,520],"answer":"Harbor"}
```

### task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label / smallest_count_gap / answer_only / sample 5081827815877320

- `instance_seed`: `5081827815877320`
- `word_count`: `65`
- `body_word_count`: `45`

```text
The image shows several small donut charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. For each panel, compute the count gap between Segment "Supplies" and Segment "Beauty". Which panel has the smallest gap?
Format for the "answer" field: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count / single / answer_and_annotation / sample 672395505763218

- `instance_seed`: `672395505763218`
- `word_count`: `97`
- `body_word_count`: `45`

```text
The image shows several small pie charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Among the 3 panels where Segment "Atlas" is largest, sum the counts for Segment "Pearl". What is the result?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full selected panels included in the sum.
Final answer format: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"annotation":[[120,90,380,520],[460,90,720,520]],"answer":780}
```

### task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count / single / answer_only / sample 672395505763218

- `instance_seed`: `672395505763218`
- `word_count`: `65`
- `body_word_count`: `45`

```text
The image shows several small pie charts. Each panel has the same segment legend, slice numbers are percentages, and each panel title includes its total count. Among the 3 panels where Segment "Atlas" is largest, sum the counts for Segment "Pearl". What is the result?
Final answer format: set "answer" to the requested integer; for percentage-point questions, omit the percent sign.
Example JSON:
{"answer":780}
```

### task_charts__contour_density__density_extremum_region_label / highest_density_region_label / answer_and_annotation / sample 8057688546070916

- `instance_seed`: `8057688546070916`
- `word_count`: `68`
- `body_word_count`: `27`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Find the labeled density region with the highest peak intensity.
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected density region.
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[510,220,650,355],"answer":"Delta"}
```

### task_charts__contour_density__density_extremum_region_label / highest_density_region_label / answer_only / sample 8057688546070916

- `instance_seed`: `8057688546070916`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Find the labeled density region with the highest peak intensity.
Answer field: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Delta"}
```

### task_charts__contour_density__density_extremum_region_label / lowest_density_region_label / answer_and_annotation / sample 3942466986224854

- `instance_seed`: `3942466986224854`
- `word_count`: `59`
- `body_word_count`: `19`

```text
The chart shows a labeled density field with contour regions and numeric axes. Which region has the lowest density?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected density region.
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[510,220,650,355],"answer":"Delta"}
```

### task_charts__contour_density__density_extremum_region_label / lowest_density_region_label / answer_only / sample 3942466986224854

- `instance_seed`: `3942466986224854`
- `word_count`: `37`
- `body_word_count`: `19`

```text
The chart shows a labeled density field with contour regions and numeric axes. Which region has the lowest density?
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Delta"}
```

### task_charts__contour_density__density_threshold_region_count / density_at_least_threshold_region_count / answer_and_annotation / sample 108631840029542

- `instance_seed`: `108631840029542`
- `word_count`: `73`
- `body_word_count`: `27`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. How many labeled regions have density level at least 2?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around every region matching the density-level threshold.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[210,180,330,300],[520,260,660,410]],"answer":2}
```

### task_charts__contour_density__density_threshold_region_count / density_at_least_threshold_region_count / answer_only / sample 108631840029542

- `instance_seed`: `108631840029542`
- `word_count`: `43`
- `body_word_count`: `27`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. How many labeled regions have density level at least 2?
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__contour_density__density_threshold_region_count / density_below_threshold_region_count / answer_and_annotation / sample 5509411476449482

- `instance_seed`: `5509411476449482`
- `word_count`: `78`
- `body_word_count`: `28`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Using the density-level encoding, how many regions are below level 3?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] boxes around every region matching the density-level threshold.
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[210,180,330,300],[520,260,660,410]],"answer":2}
```

### task_charts__contour_density__density_threshold_region_count / density_below_threshold_region_count / answer_only / sample 5509411476449482

- `instance_seed`: `5509411476449482`
- `word_count`: `44`
- `body_word_count`: `28`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Using the density-level encoding, how many regions are below level 3?
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__contour_density__reference_distance_extremum_label / horizontal_line_farthest_region_label / answer_and_annotation / sample 6516647067488604

- `instance_seed`: `6516647067488604`
- `word_count`: `69`
- `body_word_count`: `31`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. From the labeled contour regions, which one is farthest from the horizontal reference line?
Annotation format: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / horizontal_line_farthest_region_label / answer_only / sample 6516647067488604

- `instance_seed`: `6516647067488604`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. From the labeled contour regions, which one is farthest from the horizontal reference line?
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / horizontal_line_nearest_region_label / answer_and_annotation / sample 920429914061165

- `instance_seed`: `920429914061165`
- `word_count`: `71`
- `body_word_count`: `32`

```text
The figure shows a labeled contour-density field with numeric axes and reference marks when the question needs them. From the labeled contour regions, which one is nearest to the horizontal reference line?
Annotation format: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / horizontal_line_nearest_region_label / answer_only / sample 920429914061165

- `instance_seed`: `920429914061165`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The figure shows a labeled contour-density field with numeric axes and reference marks when the question needs them. From the labeled contour regions, which one is nearest to the horizontal reference line?
Answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / point_farthest_region_label / answer_and_annotation / sample 5840085337694920

- `instance_seed`: `5840085337694920`
- `word_count`: `71`
- `body_word_count`: `32`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the reference point labeled "R". Which region is farthest from it?
Annotation format: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / point_farthest_region_label / answer_only / sample 5840085337694920

- `instance_seed`: `5840085337694920`
- `word_count`: `50`
- `body_word_count`: `32`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the reference point labeled "R". Which region is farthest from it?
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / point_nearest_region_label / answer_and_annotation / sample 7471141348954927

- `instance_seed`: `7471141348954927`
- `word_count`: `71`
- `body_word_count`: `27`

```text
The visual shows a contour-density plot with labeled regions and density levels. Using the visible reference mark, identify the region nearest to the reference point labeled "R".
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Format for the "answer" field: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / point_nearest_region_label / answer_only / sample 7471141348954927

- `instance_seed`: `7471141348954927`
- `word_count`: `47`
- `body_word_count`: `27`

```text
The visual shows a contour-density plot with labeled regions and density levels. Using the visible reference mark, identify the region nearest to the reference point labeled "R".
Format for the "answer" field: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / vertical_line_farthest_region_label / answer_and_annotation / sample 7237159324805098

- `instance_seed`: `7237159324805098`
- `word_count`: `70`
- `body_word_count`: `31`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the vertical reference line. Which region is farthest from it?
Annotation format: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / vertical_line_farthest_region_label / answer_only / sample 7237159324805098

- `instance_seed`: `7237159324805098`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the vertical reference line. Which region is farthest from it?
Final answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / vertical_line_nearest_region_label / answer_and_annotation / sample 6964333585557058

- `instance_seed`: `6964333585557058`
- `word_count`: `75`
- `body_word_count`: `31`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the vertical reference line. Which region is nearest to it?
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] box around the selected density region.
Format for the "answer" field: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[620,330,760,470],"answer":"Lumen"}
```

### task_charts__contour_density__reference_distance_extremum_label / vertical_line_nearest_region_label / answer_only / sample 6964333585557058

- `instance_seed`: `6964333585557058`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The image shows a contour-density chart with labeled regions, numeric axes, and visible reference marks when needed. Compare region centers to the vertical reference line. Which region is nearest to it?
Answer field: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Lumen"}
```

### task_charts__contour_density__spread_extremum_region_label / narrowest_spread_region_label / answer_and_annotation / sample 5888168615762766

- `instance_seed`: `5888168615762766`
- `word_count`: `61`
- `body_word_count`: `20`

```text
The panel shows a contour-density visualization with labeled regions. Compare the contour footprints. What region label has the narrowest spread?
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected footprint region.
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[510,220,650,355],"answer":"Delta"}
```

### task_charts__contour_density__spread_extremum_region_label / narrowest_spread_region_label / answer_only / sample 5888168615762766

- `instance_seed`: `5888168615762766`
- `word_count`: `37`
- `body_word_count`: `33`

```text
The panel shows a contour-density visualization with labeled regions. Compare the contour footprints. What region label has the narrowest spread?
Answer field: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Delta"}
```

### task_charts__contour_density__spread_extremum_region_label / widest_spread_region_label / answer_and_annotation / sample 66162189445772

- `instance_seed`: `66162189445772`
- `word_count`: `62`
- `body_word_count`: `17`

```text
The panel shows a contour-density visualization with labeled regions. Which labeled region has the widest visible footprint?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected footprint region.
Format for the "answer" field: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[510,220,650,355],"answer":"Delta"}
```

### task_charts__contour_density__spread_extremum_region_label / widest_spread_region_label / answer_only / sample 66162189445772

- `instance_seed`: `66162189445772`
- `word_count`: `35`
- `body_word_count`: `17`

```text
The panel shows a contour-density visualization with labeled regions. Which labeled region has the widest visible footprint?
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"Delta"}
```

### task_charts__curve_panels__cross_panel_delta_extremum_label / single / answer_and_annotation / sample 6477803644536500

- `instance_seed`: `6477803644536500`
- `word_count`: `122`
- `body_word_count`: `52`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Using method "Daniyal", find the subplot with the maximum upward change between x = 10 and x = 40. If that method is not plotted in every subplot, treat the question as unanswerable and set the answer to exactly "unanswerable".
Required annotation format: set "annotation" to an object mapping "start_point" and "end_point" to [x,y] pixel points on the answer subplot's selected method markers; if the answer is "unanswerable", use an empty object.
Final answer format: set "answer" to the exact visible subplot label as a string, or "unanswerable" if the requested method is not plotted in every subplot.
Example JSON:
{"annotation":{"start_point":[220,360],"end_point":[460,250]},"answer":"Trade"}
```

### task_charts__curve_panels__cross_panel_delta_extremum_label / single / answer_only / sample 6477803644536500

- `instance_seed`: `6477803644536500`
- `word_count`: `82`
- `body_word_count`: `52`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Using method "Daniyal", find the subplot with the maximum upward change between x = 10 and x = 40. If that method is not plotted in every subplot, treat the question as unanswerable and set the answer to exactly "unanswerable".
Required answer format: set "answer" to the exact visible subplot label as a string, or "unanswerable" if the requested method is not plotted in every subplot.
Example JSON:
{"answer":"Trade"}
```

### task_charts__curve_panels__cross_panel_threshold_earliest_label / cross_panel_downward_threshold_earliest_label / answer_and_annotation / sample 6028107675256590

- `instance_seed`: `6028107675256590`
- `word_count`: `67`
- `body_word_count`: `29`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which subplot shows method "Sunrise" crossing downward through the threshold y = 55 at the lowest x-value?
Required annotation format: set "annotation" to one [x,y] pixel point at the answer subplot's threshold crossing.
Required answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[310,340],"answer":"A"}
```

### task_charts__curve_panels__cross_panel_threshold_earliest_label / cross_panel_downward_threshold_earliest_label / answer_only / sample 6028107675256590

- `instance_seed`: `6028107675256590`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which subplot shows method "Sunrise" crossing downward through the threshold y = 55 at the lowest x-value?
Final answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"A"}
```

### task_charts__curve_panels__cross_panel_threshold_earliest_label / cross_panel_upward_threshold_earliest_label / answer_and_annotation / sample 7323419315713487

- `instance_seed`: `7323419315713487`
- `word_count`: `71`
- `body_word_count`: `29`

```text
The figure shows several labeled line-chart subplots with shared method labels and x-axis values. For method "HLTC", which subplot crosses upward through y = 55 at the smallest x-axis value?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point at the answer subplot's threshold crossing.
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[310,340],"answer":"A"}
```

### task_charts__curve_panels__cross_panel_threshold_earliest_label / cross_panel_upward_threshold_earliest_label / answer_only / sample 7323419315713487

- `instance_seed`: `7323419315713487`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The figure shows several labeled line-chart subplots with shared method labels and x-axis values. For method "HLTC", which subplot crosses upward through y = 55 at the smallest x-axis value?
Required answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"A"}
```

### task_charts__curve_panels__curve_at_x_extremum_label / single / answer_and_annotation / sample 6429213835691669

- `instance_seed`: `6429213835691669`
- `word_count`: `69`
- `body_word_count`: `27`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which method has the largest plotted marker value at x = 12 in subplot "A"?
Required annotation format: set "annotation" to one [x,y] pixel point on the answer method marker at the requested x-value.
Final answer format: set "answer" to the exact visible method label as a string.
Example JSON:
{"annotation":[220,290],"answer":"Method B"}
```

### task_charts__curve_panels__curve_at_x_extremum_label / single / answer_only / sample 6429213835691669

- `instance_seed`: `6429213835691669`
- `word_count`: `45`
- `body_word_count`: `40`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which method has the largest plotted marker value at x = 12 in subplot "A"?
Answer field: set "answer" to the exact visible method label as a string.
Example JSON:
{"answer":"Method B"}
```

### task_charts__curve_panels__curve_intersection_count / single / answer_and_annotation / sample 8018509061081580

- `instance_seed`: `8018509061081580`
- `word_count`: `76`
- `body_word_count`: `26`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. How many crossing points are formed by "Brand" and "John" in subplot "Juncker"?
Annotation format: set "annotation" to an array of [x,y] pixel points at the visible intersections of the two requested methods; use an empty array if there are no intersections.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[260,330],[410,360]],"answer":2}
```

### task_charts__curve_panels__curve_intersection_count / single / answer_only / sample 8018509061081580

- `instance_seed`: `8018509061081580`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. How many crossing points are formed by "Brand" and "John" in subplot "Juncker"?
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__curve_panels__earliest_maximum_panel_label / single / answer_and_annotation / sample 3090284901737846

- `instance_seed`: `3090284901737846`
- `word_count`: `65`
- `body_word_count`: `25`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which subplot reaches its own method "Gath" maximum first along the x-axis?
Annotation format: set "annotation" to one [x,y] pixel point on the answer subplot's maximum marker for the requested method.
Answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[260,210],"answer":"A"}
```

### task_charts__curve_panels__earliest_maximum_panel_label / single / answer_only / sample 3090284901737846

- `instance_seed`: `3090284901737846`
- `word_count`: `43`
- `body_word_count`: `25`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Which subplot reaches its own method "Gath" maximum first along the x-axis?
Required answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"A"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / end_highest_panel_label / answer_and_annotation / sample 7526687967411948

- `instance_seed`: `7526687967411948`
- `word_count`: `67`
- `body_word_count`: `28`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. At the rightmost x-value, which subplot has the largest y-value for method "Belize"?
Required annotation format: set "annotation" to the [x,y] pixel point on the answer subplot's selected endpoint marker.
Required answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[520,180],"answer":"Trade"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / end_highest_panel_label / answer_only / sample 7526687967411948

- `instance_seed`: `7526687967411948`
- `word_count`: `48`
- `body_word_count`: `28`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. At the rightmost x-value, which subplot has the largest y-value for method "Belize"?
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"Trade"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / end_lowest_panel_label / answer_and_annotation / sample 5806520364541674

- `instance_seed`: `5806520364541674`
- `word_count`: `66`
- `body_word_count`: `27`

```text
The figure shows several labeled line-chart subplots with shared method labels and x-axis values. Compare the last marker of method "Jiutai" across subplots. Which subplot is lowest?
Required annotation format: set "annotation" to the [x,y] pixel point on the answer subplot's selected endpoint marker.
Required answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[520,520],"answer":"Energy"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / end_lowest_panel_label / answer_only / sample 5806520364541674

- `instance_seed`: `5806520364541674`
- `word_count`: `45`
- `body_word_count`: `27`

```text
The figure shows several labeled line-chart subplots with shared method labels and x-axis values. Compare the last marker of method "Jiutai" across subplots. Which subplot is lowest?
Final answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"Energy"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / start_highest_panel_label / answer_and_annotation / sample 879417710108701

- `instance_seed`: `879417710108701`
- `word_count`: `67`
- `body_word_count`: `28`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. For method "Travel", which subplot has the highest starting marker?
Required annotation format: set "annotation" to the [x,y] pixel point on the answer subplot's selected endpoint marker.
Final answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[210,190],"answer":"RunA"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / start_highest_panel_label / answer_only / sample 879417710108701

- `instance_seed`: `879417710108701`
- `word_count`: `45`
- `body_word_count`: `28`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. For method "Travel", which subplot has the highest starting marker?
Answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"RunA"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / start_lowest_panel_label / answer_and_annotation / sample 4139626913701027

- `instance_seed`: `4139626913701027`
- `word_count`: `65`
- `body_word_count`: `28`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. At the leftmost x-value, which subplot has the smallest y-value for method "Kucera"?
Annotation format: set "annotation" to the [x,y] pixel point on the answer subplot's selected endpoint marker.
Answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[210,510],"answer":"RunB"}
```

### task_charts__curve_panels__endpoint_rank_panel_label / start_lowest_panel_label / answer_only / sample 4139626913701027

- `instance_seed`: `4139626913701027`
- `word_count`: `46`
- `body_word_count`: `28`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. At the leftmost x-value, which subplot has the smallest y-value for method "Kucera"?
Final answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"RunB"}
```

### task_charts__curve_panels__global_value_extremum_panel_label / overall_maximum_value_panel_label / answer_and_annotation / sample 3220811734460154

- `instance_seed`: `3220811734460154`
- `word_count`: `66`
- `body_word_count`: `25`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Which subplot has the global maximum y-value among all visible markers?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point on the overall maximum marker.
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[460,180],"answer":"Energy"}
```

### task_charts__curve_panels__global_value_extremum_panel_label / overall_maximum_value_panel_label / answer_only / sample 3220811734460154

- `instance_seed`: `3220811734460154`
- `word_count`: `43`
- `body_word_count`: `25`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Which subplot has the global maximum y-value among all visible markers?
Final answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"Energy"}
```

### task_charts__curve_panels__global_value_extremum_panel_label / overall_minimum_value_panel_label / answer_and_annotation / sample 6846758216188864

- `instance_seed`: `6846758216188864`
- `word_count`: `66`
- `body_word_count`: `25`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Which subplot has the global minimum y-value among all visible markers?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point on the overall minimum marker.
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":[340,520],"answer":"Trade"}
```

### task_charts__curve_panels__global_value_extremum_panel_label / overall_minimum_value_panel_label / answer_only / sample 6846758216188864

- `instance_seed`: `6846758216188864`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. Which subplot has the global minimum y-value among all visible markers?
Answer field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"Trade"}
```

### task_charts__curve_panels__panel_curve_threshold_crossing_count / panel_curve_downward_threshold_crossing_count / answer_and_annotation / sample 2264288718147693

- `instance_seed`: `2264288718147693`
- `word_count`: `65`
- `body_word_count`: `25`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Within subplot "Profile", how many method curves cross downward through y = 45?
Annotation format: set "annotation" to an array of [x,y] pixel points on every curve-threshold crossing in the requested subplot.
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[260,340],[410,340]],"answer":2}
```

### task_charts__curve_panels__panel_curve_threshold_crossing_count / panel_curve_downward_threshold_crossing_count / answer_only / sample 2264288718147693

- `instance_seed`: `2264288718147693`
- `word_count`: `41`
- `body_word_count`: `25`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. Within subplot "Profile", how many method curves cross downward through y = 45?
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__curve_panels__panel_curve_threshold_crossing_count / panel_curve_upward_threshold_crossing_count / answer_and_annotation / sample 5435155835976267

- `instance_seed`: `5435155835976267`
- `word_count`: `71`
- `body_word_count`: `29`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. Using subplot "E", count each curve that crosses upward through the threshold y = 55.
Required annotation format: set "annotation" to an array of [x,y] pixel points on every curve-threshold crossing in the requested subplot.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[260,340],[410,340]],"answer":2}
```

### task_charts__curve_panels__panel_curve_threshold_crossing_count / panel_curve_upward_threshold_crossing_count / answer_only / sample 5435155835976267

- `instance_seed`: `5435155835976267`
- `word_count`: `45`
- `body_word_count`: `29`

```text
The panel shows a grid of curve plots with labeled subplots, markers, and method legends. Using subplot "E", count each curve that crosses upward through the threshold y = 55.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__curve_panels__panel_spread_extremum_label / largest_panel_spread_label / answer_and_annotation / sample 7699290225278696

- `instance_seed`: `7699290225278696`
- `word_count`: `84`
- `body_word_count`: `30`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. Across subplots, which one has the widest range of visible marker y-values?
Format for the "annotation" field: set "annotation" to an object mapping "min_point" and "max_point" to [x,y] pixel points on the answer subplot's minimum and maximum markers.
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":{"min_point":[260,520],"max_point":[460,180]},"answer":"Trade"}
```

### task_charts__curve_panels__panel_spread_extremum_label / largest_panel_spread_label / answer_only / sample 7699290225278696

- `instance_seed`: `7699290225278696`
- `word_count`: `50`
- `body_word_count`: `30`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. Across subplots, which one has the widest range of visible marker y-values?
Format for the "answer" field: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"Trade"}
```

### task_charts__curve_panels__panel_spread_extremum_label / smallest_panel_spread_label / answer_and_annotation / sample 4610986074316942

- `instance_seed`: `4610986074316942`
- `word_count`: `80`
- `body_word_count`: `32`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. Find the subplot with the smallest difference between its minimum and maximum plotted markers.
Annotation format: set "annotation" to an object mapping "min_point" and "max_point" to [x,y] pixel points on the answer subplot's minimum and maximum markers.
Answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"annotation":{"min_point":[260,330],"max_point":[460,300]},"answer":"A"}
```

### task_charts__curve_panels__panel_spread_extremum_label / smallest_panel_spread_label / answer_only / sample 4610986074316942

- `instance_seed`: `4610986074316942`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The image shows a multi-panel line figure. Each subplot has labeled methods, shared x-axis ticks, and plotted markers. Find the subplot with the smallest difference between its minimum and maximum plotted markers.
Answer format: set "answer" to the exact visible subplot label as a string.
Example JSON:
{"answer":"A"}
```

### task_charts__curve_panels__threshold_series_count / above_threshold_series_count / answer_and_annotation / sample 2238840476939370

- `instance_seed`: `2238840476939370`
- `word_count`: `76`
- `body_word_count`: `26`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. How many curves in subplot "B" are above y = 65 at x = 44?
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on the method markers that satisfy the threshold at the requested x-value.
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[220,360],[220,290]],"answer":2}
```

### task_charts__curve_panels__threshold_series_count / above_threshold_series_count / answer_only / sample 2238840476939370

- `instance_seed`: `2238840476939370`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The visual shows a multi-panel line plot with labeled subplots and method curves. How many curves in subplot "B" are above y = 65 at x = 44?
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__curve_panels__threshold_series_count / below_threshold_series_count / answer_and_annotation / sample 163684918553120

- `instance_seed`: `163684918553120`
- `word_count`: `75`
- `body_word_count`: `29`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. At x = 66 in subplot "A", count the methods whose y-value is less than 45.
Required annotation format: set "annotation" to an array of [x,y] pixel points on the method markers that satisfy the threshold at the requested x-value.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[220,360],[220,290]],"answer":2}
```

### task_charts__curve_panels__threshold_series_count / below_threshold_series_count / answer_only / sample 163684918553120

- `instance_seed`: `163684918553120`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The chart shows multiple line-plot panels with the same method labels repeated across panels. At x = 66 in subplot "A", count the methods whose y-value is less than 45.
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__dashboard__category_extremum_panel_label / largest_category_panel_label / answer_and_annotation / sample 4637304426015850

- `instance_seed`: `4637304426015850`
- `word_count`: `96`
- `body_word_count`: `56`

```text
The image shows a dashboard with 5 titled panels named "Summit Radar", "Quartz Radar", "Beacon Radar", "Atlas Donut", and "Slate Bar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. For the shared category "Birch", report the panel with the greatest value.
Annotation format: set "annotation" to one [x,y] pixel point on the target category mark in the answer panel.
Answer field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[610,244],"answer":"Orchid Bar"}
```

### task_charts__dashboard__category_extremum_panel_label / largest_category_panel_label / answer_only / sample 4637304426015850

- `instance_seed`: `4637304426015850`
- `word_count`: `77`
- `body_word_count`: `56`

```text
The image shows a dashboard with 5 titled panels named "Summit Radar", "Quartz Radar", "Beacon Radar", "Atlas Donut", and "Slate Bar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. For the shared category "Birch", report the panel with the greatest value.
Format for the "answer" field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__category_extremum_panel_label / smallest_category_panel_label / answer_and_annotation / sample 8590407407031234

- `instance_seed`: `8590407407031234`
- `word_count`: `98`
- `body_word_count`: `58`

```text
The image shows a dashboard with 6 titled panels named "TrialB Donut", "SampleA Radar", "VariantB Donut", "RunB Line", "GroupC Donut", and "TrialA Radar". It uses a shared category/color key with 6 possible category labels, and exact integer values are shown for each plotted category mark. Look only at category "Teal" in each panel. Which panel is smallest?
Annotation format: set "annotation" to one [x,y] pixel point on the target category mark in the answer panel.
Answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[610,244],"answer":"Orchid Bar"}
```

### task_charts__dashboard__category_extremum_panel_label / smallest_category_panel_label / answer_only / sample 8590407407031234

- `instance_seed`: `8590407407031234`
- `word_count`: `76`
- `body_word_count`: `71`

```text
The image shows a dashboard with 6 titled panels named "TrialB Donut", "SampleA Radar", "VariantB Donut", "RunB Line", "GroupC Donut", and "TrialA Radar". It uses a shared category/color key with 6 possible category labels, and exact integer values are shown for each plotted category mark. Look only at category "Teal" in each panel. Which panel is smallest?
Answer field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__category_panel_condition_count / category_panel_greater_than_threshold_count / answer_and_annotation / sample 7477658460701177

- `instance_seed`: `7477658460701177`
- `word_count`: `103`
- `body_word_count`: `60`

```text
The image shows a dashboard with 5 titled panels named "SampleC Donut", "SiteB Line", "RunB Donut", "BatchC Radar", and "BatchA Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. For category "Ruby" across all panels, count the panels where its value is greater than 81.
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on each counted category mark.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[190,240],[790,245],[845,298]],"answer":3}
```

### task_charts__dashboard__category_panel_condition_count / category_panel_greater_than_threshold_count / answer_only / sample 7477658460701177

- `instance_seed`: `7477658460701177`
- `word_count`: `73`
- `body_word_count`: `69`

```text
The image shows a dashboard with 5 titled panels named "SampleC Donut", "SiteB Line", "RunB Donut", "BatchC Radar", and "BatchA Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. For category "Ruby" across all panels, count the panels where its value is greater than 81.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__dashboard__category_panel_condition_count / category_panel_less_than_threshold_count / answer_and_annotation / sample 8663298326247518

- `instance_seed`: `8663298326247518`
- `word_count`: `102`
- `body_word_count`: `65`

```text
The image shows a dashboard with 8 titled panels named "Grove Radar", "Summit Bar", "Ruby Line", "Olive Bar", "Slate Radar", "Maple Line", "Saffron Line", and "Silver Donut". It uses a shared category/color key with 4 possible category labels, and exact integer values are shown for each plotted category mark. Across the dashboard, count panels in which category "Nova" has a value less than 46.
Annotation format: set "annotation" to an array of [x,y] pixel points on each counted category mark.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[190,240],[790,245],[845,298]],"answer":3}
```

### task_charts__dashboard__category_panel_condition_count / category_panel_less_than_threshold_count / answer_only / sample 8663298326247518

- `instance_seed`: `8663298326247518`
- `word_count`: `79`
- `body_word_count`: `65`

```text
The image shows a dashboard with 8 titled panels named "Grove Radar", "Summit Bar", "Ruby Line", "Olive Bar", "Slate Radar", "Maple Line", "Saffron Line", and "Silver Donut". It uses a shared category/color key with 4 possible category labels, and exact integer values are shown for each plotted category mark. Across the dashboard, count panels in which category "Nova" has a value less than 46.
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__dashboard__category_total_extremum_label / largest_category_total_label / answer_and_annotation / sample 7396521182563627

- `instance_seed`: `7396521182563627`
- `word_count`: `152`
- `body_word_count`: `80`

```text
The image shows a dashboard with 6 titled panels named "Drena Donut", "Patak Bar", "Record Line", "Xanti Line", "Almatine Radar", and "Rickard Radar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Sum each category across every panel. Which category has the largest total? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on that category's mark in every panel; if the answer is "unanswerable", use an empty array.
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"annotation":[[180,220],[475,240],[790,260],[1080,245]],"answer":"Mica"}
```

### task_charts__dashboard__category_total_extremum_label / largest_category_total_label / answer_only / sample 7396521182563627

- `instance_seed`: `7396521182563627`
- `word_count`: `112`
- `body_word_count`: `80`

```text
The image shows a dashboard with 6 titled panels named "Drena Donut", "Patak Bar", "Record Line", "Xanti Line", "Almatine Radar", and "Rickard Radar". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Sum each category across every panel. Which category has the largest total? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"answer":"Mica"}
```

### task_charts__dashboard__category_total_extremum_label / smallest_category_total_label / answer_and_annotation / sample 2728616631873392

- `instance_seed`: `2728616631873392`
- `word_count`: `149`
- `body_word_count`: `81`

```text
The image shows a dashboard with 7 titled panels named "Compiler Donut", "Optimizer Donut", "Fusion Line", "Clocking Line", "Network Radar", "Accuracy Bar", and "Debug Bar". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the smallest total across all dashboard panels? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Required annotation format: set "annotation" to an array of [x,y] pixel points on that category's mark in every panel; if the answer is "unanswerable", use an empty array.
Required answer format: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"annotation":[[180,220],[475,240],[790,260],[1080,245]],"answer":"Mica"}
```

### task_charts__dashboard__category_total_extremum_label / smallest_category_total_label / answer_only / sample 2728616631873392

- `instance_seed`: `2728616631873392`
- `word_count`: `113`
- `body_word_count`: `81`

```text
The image shows a dashboard with 7 titled panels named "Compiler Donut", "Optimizer Donut", "Fusion Line", "Clocking Line", "Network Radar", "Accuracy Bar", and "Debug Bar". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the smallest total across all dashboard panels? If any category is not shown in every dashboard panel, treat the question as unanswerable and set the answer to exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible category label as a string, or "unanswerable" if any category is not shown in every dashboard panel.
Example JSON:
{"answer":"Mica"}
```

### task_charts__dashboard__global_value_extremum_category_label / global_maximum_value_category_label / answer_and_annotation / sample 2780123190702888

- `instance_seed`: `2780123190702888`
- `word_count`: `100`
- `body_word_count`: `64`

```text
The image shows a dashboard with 9 titled panels named "SiteB Bar", "TrialC Bar", "CohortB Bar", "ModelB Line", "VariantC Bar", "VariantA Radar", "Control Donut", "TrialB Bar", and "Phase2 Bar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the single largest value anywhere in the dashboard?
Annotation format: set "annotation" to one [x,y] pixel point on the global maximum category mark.
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[610,244],"answer":"Mica"}
```

### task_charts__dashboard__global_value_extremum_category_label / global_maximum_value_category_label / answer_only / sample 2780123190702888

- `instance_seed`: `2780123190702888`
- `word_count`: `81`
- `body_word_count`: `77`

```text
The image shows a dashboard with 9 titled panels named "SiteB Bar", "TrialC Bar", "CohortB Bar", "ModelB Line", "VariantC Bar", "VariantA Radar", "Control Donut", "TrialB Bar", and "Phase2 Bar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Which category label has the single largest value anywhere in the dashboard?
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Mica"}
```

### task_charts__dashboard__global_value_extremum_category_label / global_minimum_value_category_label / answer_and_annotation / sample 1120092161629110

- `instance_seed`: `1120092161629110`
- `word_count`: `97`
- `body_word_count`: `55`

```text
The image shows a dashboard with 5 titled panels named "Cipher Line", "PacketLoss Line", "Mixture Donut", "Precision Radar", and "Ramp Donut". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Looking across all panels, which category has the lowest value overall?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point on the global minimum category mark.
Format for the "answer" field: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[610,244],"answer":"Mica"}
```

### task_charts__dashboard__global_value_extremum_category_label / global_minimum_value_category_label / answer_only / sample 1120092161629110

- `instance_seed`: `1120092161629110`
- `word_count`: `75`
- `body_word_count`: `55`

```text
The image shows a dashboard with 5 titled panels named "Cipher Line", "PacketLoss Line", "Mixture Donut", "Precision Radar", and "Ramp Donut". It uses a shared category/color key with 10 possible category labels, and exact integer values are shown for each plotted category mark. Looking across all panels, which category has the lowest value overall?
Format for the "answer" field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Mica"}
```

### task_charts__dashboard__panel_total_extremum_label / largest_panel_total_label / answer_and_annotation / sample 794730572079354

- `instance_seed`: `794730572079354`
- `word_count`: `111`
- `body_word_count`: `63`

```text
The image shows a dashboard with 8 titled panels named "SampleA Bar", "BatchC Donut", "ModelB Line", "RunC Radar", "BatchB Bar", "TrialB Line", "ModelC Donut", and "VariantC Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Sum the category values within each panel. Which panel has the largest total?
Annotation format: set "annotation" to an array of [x,y] pixel points on every category mark in the answer panel.
Final answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[[430,218],[512,337],[588,260],[642,232]],"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_total_extremum_label / largest_panel_total_label / answer_only / sample 794730572079354

- `instance_seed`: `794730572079354`
- `word_count`: `82`
- `body_word_count`: `63`

```text
The image shows a dashboard with 8 titled panels named "SampleA Bar", "BatchC Donut", "ModelB Line", "RunC Radar", "BatchB Bar", "TrialB Line", "ModelC Donut", and "VariantC Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Sum the category values within each panel. Which panel has the largest total?
Required answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_total_extremum_label / smallest_panel_total_label / answer_and_annotation / sample 152854471729228

- `instance_seed`: `152854471729228`
- `word_count`: `108`
- `body_word_count`: `61`

```text
The image shows a dashboard with 8 titled panels named "Ivory Line", "Summit Radar", "Atlas Radar", "Valley Bar", "Cedar Bar", "Flint Radar", "Crimson Radar", and "Harbor Line". It uses a shared category/color key with 4 possible category labels, and exact integer values are shown for each plotted category mark. Which panel title corresponds to the lowest total over its categories?
Annotation format: set "annotation" to an array of [x,y] pixel points on every category mark in the answer panel.
Answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":[[430,218],[512,337],[588,260],[642,232]],"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_total_extremum_label / smallest_panel_total_label / answer_only / sample 152854471729228

- `instance_seed`: `152854471729228`
- `word_count`: `82`
- `body_word_count`: `61`

```text
The image shows a dashboard with 8 titled panels named "Ivory Line", "Summit Radar", "Atlas Radar", "Valley Bar", "Cedar Bar", "Flint Radar", "Crimson Radar", and "Harbor Line". It uses a shared category/color key with 4 possible category labels, and exact integer values are shown for each plotted category mark. Which panel title corresponds to the lowest total over its categories?
Format for the "answer" field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_value_range_extremum_label / largest_panel_value_range_label / answer_and_annotation / sample 2709582525960747

- `instance_seed`: `2709582525960747`
- `word_count`: `124`
- `body_word_count`: `66`

```text
The image shows a dashboard with 8 titled panels named "Cesaro Line", "Linga Line", "Savoy Line", "Calleigh Bar", "Matas Bar", "Hying Radar", "Kahmila Radar", and "Handerhan Line". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Across the dashboard, which panel has the greatest difference between its largest and smallest category values?
Format for the "annotation" field: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on the two category marks that define the answer panel's range.
Format for the "answer" field: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_value_range_extremum_label / largest_panel_value_range_label / answer_only / sample 2709582525960747

- `instance_seed`: `2709582525960747`
- `word_count`: `85`
- `body_word_count`: `66`

```text
The image shows a dashboard with 8 titled panels named "Cesaro Line", "Linga Line", "Savoy Line", "Calleigh Bar", "Matas Bar", "Hying Radar", "Kahmila Radar", and "Handerhan Line". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Across the dashboard, which panel has the greatest difference between its largest and smallest category values?
Final answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_value_range_extremum_label / smallest_panel_value_range_label / answer_and_annotation / sample 1569723762398953

- `instance_seed`: `1569723762398953`
- `word_count`: `115`
- `body_word_count`: `61`

```text
The image shows a dashboard with 6 titled panels named "Dallary Donut", "Eugune Radar", "Quinty Line", "Chrishayla Line", "Zahkir Donut", and "Zavonte Line". It uses a shared category/color key with 8 possible category labels, and exact integer values are shown for each plotted category mark. Find the panel whose category values span the narrowest range. What is its panel title?
Required annotation format: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on the two category marks that define the answer panel's range.
Required answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_value_range_extremum_label / smallest_panel_value_range_label / answer_only / sample 1569723762398953

- `instance_seed`: `1569723762398953`
- `word_count`: `79`
- `body_word_count`: `61`

```text
The image shows a dashboard with 6 titled panels named "Dallary Donut", "Eugune Radar", "Quinty Line", "Chrishayla Line", "Zahkir Donut", and "Zavonte Line". It uses a shared category/color key with 8 possible category labels, and exact integer values are shown for each plotted category mark. Find the panel whose category values span the narrowest range. What is its panel title?
Answer format: set "answer" to the exact visible panel title as a string.
Example JSON:
{"answer":"Orchid Bar"}
```

### task_charts__dashboard__panel_value_range_value / single / answer_and_annotation / sample 4676936198073555

- `instance_seed`: `4676936198073555`
- `word_count`: `109`
- `body_word_count`: `59`

```text
The image shows a dashboard with 5 titled panels named "Gunns Radar", "Rinnah Donut", "Hayk Line", "Overlie Line", and "Rua Bar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Using only "Overlie Line", what range do its category values span from smallest to largest?
Format for the "annotation" field: set "annotation" to an object mapping "largest_value" and "smallest_value" to [x,y] pixel points on those category marks in the named panel.
Format for the "answer" field: set "answer" to the requested integer difference.
Example JSON:
{"annotation":{"largest_value":[430,218],"smallest_value":[512,337]},"answer":37}
```

### task_charts__dashboard__panel_value_range_value / single / answer_only / sample 4676936198073555

- `instance_seed`: `4676936198073555`
- `word_count`: `73`
- `body_word_count`: `59`

```text
The image shows a dashboard with 5 titled panels named "Gunns Radar", "Rinnah Donut", "Hayk Line", "Overlie Line", and "Rua Bar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Using only "Overlie Line", what range do its category values span from smallest to largest?
Required answer format: set "answer" to the requested integer difference.
Example JSON:
{"answer":37}
```

### task_charts__dashboard__source_rank_target_value / largest_source_rank_target_value / answer_and_annotation / sample 8576475049260742

- `instance_seed`: `8576475049260742`
- `word_count`: `102`
- `body_word_count`: `56`

```text
The image shows a dashboard with 4 titled panels named "VariantC Donut", "CaseB Radar", "SiteC Bar", and "Control Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Find the largest category in "CaseB Radar". Report its integer value from "Control Radar".
Required annotation format: set "annotation" to an object mapping "source_panel" and "target_panel" to [x,y] pixel points on the selected category marks in those panels.
Required answer format: set "answer" to the requested integer value.
Example JSON:
{"annotation":{"source_panel":[180,220],"target_panel":[860,260]},"answer":47}
```

### task_charts__dashboard__source_rank_target_value / largest_source_rank_target_value / answer_only / sample 8576475049260742

- `instance_seed`: `8576475049260742`
- `word_count`: `72`
- `body_word_count`: `56`

```text
The image shows a dashboard with 4 titled panels named "VariantC Donut", "CaseB Radar", "SiteC Bar", and "Control Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. Find the largest category in "CaseB Radar". Report its integer value from "Control Radar".
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"answer":47}
```

### task_charts__dashboard__source_rank_target_value / smallest_source_rank_target_value / answer_and_annotation / sample 8571842837276742

- `instance_seed`: `8571842837276742`
- `word_count`: `108`
- `body_word_count`: `58`

```text
The image shows a dashboard with 4 titled panels named "Spectrum Line", "Bayes Line", "Hypothesis Line", and "Timestep Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. First rank categories in "Bayes Line"; for the smallest one, what value appears in "Hypothesis Line"?
Format for the "annotation" field: set "annotation" to an object mapping "source_panel" and "target_panel" to [x,y] pixel points on the selected category marks in those panels.
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"annotation":{"source_panel":[180,220],"target_panel":[860,260]},"answer":47}
```

### task_charts__dashboard__source_rank_target_value / smallest_source_rank_target_value / answer_only / sample 8571842837276742

- `instance_seed`: `8571842837276742`
- `word_count`: `71`
- `body_word_count`: `67`

```text
The image shows a dashboard with 4 titled panels named "Spectrum Line", "Bayes Line", "Hypothesis Line", and "Timestep Radar". It uses a shared category/color key with 7 possible category labels, and exact integer values are shown for each plotted category mark. First rank categories in "Bayes Line"; for the smallest one, what value appears in "Hypothesis Line"?
Answer field: set "answer" to the requested integer value.
Example JSON:
{"answer":47}
```

### task_charts__dashboard__statement_option_selection_label / single / answer_and_annotation / sample 4753299646627818

- `instance_seed`: `4753299646627818`
- `word_count`: `100`
- `body_word_count`: `56`

```text
The image shows a dashboard with 6 titled panels named "Echo Bar", "Olive Line", "Meadow Radar", "Ivory Bar", "Quartz Radar", and "Beacon Line". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Select the option letter for the statement that is false.
Annotation format: set "annotation" to an array of two [x,y] pixel points on the chart marks that verify the selected statement.
Answer format: set "answer" to the selected option letter as a capital letter.
Example JSON:
{"annotation":[[175,240],[805,250]],"answer":"C"}
```

### task_charts__dashboard__statement_option_selection_label / single / answer_only / sample 4753299646627818

- `instance_seed`: `4753299646627818`
- `word_count`: `73`
- `body_word_count`: `69`

```text
The image shows a dashboard with 6 titled panels named "Echo Bar", "Olive Line", "Meadow Radar", "Ivory Bar", "Quartz Radar", and "Beacon Line". It uses a shared category/color key with 5 possible category labels, and exact integer values are shown for each plotted category mark. Select the option letter for the statement that is false.
Answer field: set "answer" to the selected option letter as a capital letter.
Example JSON:
{"answer":"C"}
```

### task_charts__density_curve__density_at_x_extremum_label / highest_density_at_x_label / answer_and_annotation / sample 573990986045704

- `instance_seed`: `573990986045704`
- `word_count`: `73`
- `body_word_count`: `34`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Using the vertical reference line at x = 36, find the curve label with the greatest density.
Annotation format: set "annotation" to the [x,y] pixel point on the answer curve at the marked x-position.
Final answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[420,245],"answer":"Orchid"}
```

### task_charts__density_curve__density_at_x_extremum_label / highest_density_at_x_label / answer_only / sample 573990986045704

- `instance_seed`: `573990986045704`
- `word_count`: `52`
- `body_word_count`: `34`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Using the vertical reference line at x = 36, find the curve label with the greatest density.
Required answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__density_at_x_extremum_label / lowest_density_at_x_label / answer_and_annotation / sample 5100677818010742

- `instance_seed`: `5100677818010742`
- `word_count`: `72`
- `body_word_count`: `34`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Using the vertical reference line at x = 27, find the curve label with the smallest density.
Annotation format: set "annotation" to the [x,y] pixel point on the answer curve at the marked x-position.
Answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[420,245],"answer":"Orchid"}
```

### task_charts__density_curve__density_at_x_extremum_label / lowest_density_at_x_label / answer_only / sample 5100677818010742

- `instance_seed`: `5100677818010742`
- `word_count`: `52`
- `body_word_count`: `34`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Using the vertical reference line at x = 27, find the curve label with the smallest density.
Final answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__interval_mass_extremum_label / greatest_interval_mass_label / answer_and_annotation / sample 5572810559113893

- `instance_seed`: `5572810559113893`
- `word_count`: `70`
- `body_word_count`: `30`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Within the shaded interval "47-68", which curve has the greatest density mass?
Required annotation format: set "annotation" to an [x,y] pixel point on the answer curve inside the marked interval.
Required answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[345,382],"answer":"Orchid"}
```

### task_charts__density_curve__interval_mass_extremum_label / greatest_interval_mass_label / answer_only / sample 5572810559113893

- `instance_seed`: `5572810559113893`
- `word_count`: `47`
- `body_word_count`: `43`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Within the shaded interval "47-68", which curve has the greatest density mass?
Answer field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__interval_mass_extremum_label / least_interval_mass_label / answer_and_annotation / sample 2369505732519324

- `instance_seed`: `2369505732519324`
- `word_count`: `66`
- `body_word_count`: `28`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which labeled density curve contributes the least mass inside "55-87"?
Annotation format: set "annotation" to an [x,y] pixel point on the answer curve inside the marked interval.
Answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[345,382],"answer":"Orchid"}
```

### task_charts__density_curve__interval_mass_extremum_label / least_interval_mass_label / answer_only / sample 2369505732519324

- `instance_seed`: `2369505732519324`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which labeled density curve contributes the least mass inside "55-87"?
Answer field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__mean_extremum_label / highest_mean_label / answer_and_annotation / sample 8083231695611674

- `instance_seed`: `8083231695611674`
- `word_count`: `66`
- `body_word_count`: `27`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Identify the density curve with the rightmost center-of-mass marker.
Annotation format: set "annotation" to the [x,y] pixel point at the center of the answer curve mean marker.
Answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[228,522],"answer":"Orchid"}
```

### task_charts__density_curve__mean_extremum_label / highest_mean_label / answer_only / sample 8083231695611674

- `instance_seed`: `8083231695611674`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Identify the density curve with the rightmost center-of-mass marker.
Answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__mean_extremum_label / lowest_mean_label / answer_and_annotation / sample 5518048356410395

- `instance_seed`: `5518048356410395`
- `word_count`: `66`
- `body_word_count`: `26`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which labeled curve has the lowest mean x-value?
Annotation format: set "annotation" to the [x,y] pixel point at the center of the answer curve mean marker.
Final answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[228,522],"answer":"Orchid"}
```

### task_charts__density_curve__mean_extremum_label / lowest_mean_label / answer_only / sample 5518048356410395

- `instance_seed`: `5518048356410395`
- `word_count`: `46`
- `body_word_count`: `26`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which labeled curve has the lowest mean x-value?
Format for the "answer" field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__mode_location_extremum_label / leftmost_mode_label / answer_and_annotation / sample 5706653524768073

- `instance_seed`: `5706653524768073`
- `word_count`: `66`
- `body_word_count`: `27`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which density curve has the leftmost visible peak marker?
Annotation format: set "annotation" to the [x,y] pixel point at the center of the answer curve peak marker.
Answer format: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[398,213],"answer":"Orchid"}
```

### task_charts__density_curve__mode_location_extremum_label / leftmost_mode_label / answer_only / sample 5706653524768073

- `instance_seed`: `5706653524768073`
- `word_count`: `47`
- `body_word_count`: `27`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which density curve has the leftmost visible peak marker?
Format for the "answer" field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__density_curve__mode_location_extremum_label / rightmost_mode_label / answer_and_annotation / sample 825052287932063

- `instance_seed`: `825052287932063`
- `word_count`: `75`
- `body_word_count`: `30`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which label corresponds to the curve whose main peak lies farthest right?
Format for the "annotation" field: set "annotation" to the [x,y] pixel point at the center of the answer curve peak marker.
Format for the "answer" field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"annotation":[398,213],"answer":"Orchid"}
```

### task_charts__density_curve__mode_location_extremum_label / rightmost_mode_label / answer_only / sample 825052287932063

- `instance_seed`: `825052287932063`
- `word_count`: `47`
- `body_word_count`: `43`

```text
The image shows several smooth labeled density curves with a legend and exact x-axis reference marks when needed. Which label corresponds to the curve whose main peak lies farthest right?
Answer field: set "answer" to the exact visible density-curve label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__dumbbell__absolute_gap_threshold_count / absolute_gap_at_least_threshold_count / answer_and_annotation / sample 7753372545278570

- `instance_seed`: `7753372545278570`
- `word_count`: `120`
- `body_word_count`: `58`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many categories have the two series differing by at least 28 units?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__absolute_gap_threshold_count / absolute_gap_at_least_threshold_count / answer_only / sample 7753372545278570

- `instance_seed`: `7753372545278570`
- `word_count`: `72`
- `body_word_count`: `58`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many categories have the two series differing by at least 28 units?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__dumbbell__absolute_gap_threshold_count / absolute_gap_at_most_threshold_count / answer_and_annotation / sample 2511738239517459

- `instance_seed`: `2511738239517459`
- `word_count`: `120`
- `body_word_count`: `60`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Using the shared horizontal axis, how many rows have a dot-to-dot separation at most 20?
Annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__absolute_gap_threshold_count / absolute_gap_at_most_threshold_count / answer_only / sample 2511738239517459

- `instance_seed`: `2511738239517459`
- `word_count`: `74`
- `body_word_count`: `60`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Using the shared horizontal axis, how many rows have a dot-to-dot separation at most 20?
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__dumbbell__gap_rank_row_label / largest_gap_rank_row_label / answer_and_annotation / sample 5303107782709320

- `instance_seed`: `5303107782709320`
- `word_count`: `109`
- `body_word_count`: `66`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Rank rows by the absolute length of the gray connector between the two dots. Which row has the second largest gap?
Annotation format: set "annotation" to one segment [[x1, y1], [x2, y2]], using the two colored dot centers for the supporting row.
Answer format: set "answer" to the exact visible row label as a string.
Example JSON:
{"annotation":[[276,231],[1032,231]],"answer":"Harbor"}
```

### task_charts__dumbbell__gap_rank_row_label / largest_gap_rank_row_label / answer_only / sample 5303107782709320

- `instance_seed`: `5303107782709320`
- `word_count`: `83`
- `body_word_count`: `66`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Rank rows by the absolute length of the gray connector between the two dots. Which row has the second largest gap?
Answer format: set "answer" to the exact visible row label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__dumbbell__gap_rank_row_label / smallest_gap_rank_row_label / answer_and_annotation / sample 7447560294611127

- `instance_seed`: `7447560294611127`
- `word_count`: `106`
- `body_word_count`: `63`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Sort the rows by absolute dot-to-dot gap, ignoring which color is larger. Which row has the smallest gap?
Annotation format: set "annotation" to one segment [[x1, y1], [x2, y2]], using the two colored dot centers for the supporting row.
Answer format: set "answer" to the exact visible row label as a string.
Example JSON:
{"annotation":[[276,231],[1032,231]],"answer":"Harbor"}
```

### task_charts__dumbbell__gap_rank_row_label / smallest_gap_rank_row_label / answer_only / sample 7447560294611127

- `instance_seed`: `7447560294611127`
- `word_count`: `81`
- `body_word_count`: `63`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. Sort the rows by absolute dot-to-dot gap, ignoring which color is larger. Which row has the smallest gap?
Required answer format: set "answer" to the exact visible row label as a string.
Example JSON:
{"answer":"Harbor"}
```

### task_charts__dumbbell__side_winner_count / series_a_greater_threshold_count / answer_and_annotation / sample 6842348674244685

- `instance_seed`: `6842348674244685`
- `word_count`: `123`
- `body_word_count`: `57`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Oyster" at least 16 units greater than "Steers"?
Format for the "annotation" field: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__side_winner_count / series_a_greater_threshold_count / answer_only / sample 6842348674244685

- `instance_seed`: `6842348674244685`
- `word_count`: `70`
- `body_word_count`: `66`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Oyster" at least 16 units greater than "Steers"?
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__dumbbell__side_winner_count / series_b_greater_threshold_count / answer_and_annotation / sample 6024682079833462

- `instance_seed`: `6024682079833462`
- `word_count`: `119`
- `body_word_count`: `57`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Hillis" greater than "Modrall" by at least 16?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two colored dot centers for one row that satisfies the condition; use [] if no rows match.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[276,231],[1032,231]],[[318,355],[1032,355]],[[284,541],[1032,541]]],"answer":3}
```

### task_charts__dumbbell__side_winner_count / series_b_greater_threshold_count / answer_only / sample 6024682079833462

- `instance_seed`: `6024682079833462`
- `word_count`: `70`
- `body_word_count`: `57`

```text
The image shows a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row give the values for the two legend series on the shared horizontal numeric axis. The gray connector shows the gap between the two dots. How many rows have "Hillis" greater than "Modrall" by at least 16?
Answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__error_interval__interval_width_rank_label / narrowest_interval_label / answer_and_annotation / sample 3779215526835139

- `instance_seed`: `3779215526835139`
- `word_count`: `60`
- `body_word_count`: `23`

```text
The image shows a vertical dot-and-whisker interval chart with labeled categories and printed interval endpoints. What category label corresponds to the narrowest interval?
Annotation format: set "annotation" to the selected interval's lower-to-upper segment as [[x0,y0],[x1,y1]].
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":[[310,268],[610,268]],"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / narrowest_interval_label / answer_only / sample 3779215526835139

- `instance_seed`: `3779215526835139`
- `word_count`: `40`
- `body_word_count`: `23`

```text
The image shows a vertical dot-and-whisker interval chart with labeled categories and printed interval endpoints. What category label corresponds to the narrowest interval?
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / second_narrowest_interval_label / answer_and_annotation / sample 5497961587865673

- `instance_seed`: `5497961587865673`
- `word_count`: `61`
- `body_word_count`: `23`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. Which category has the second narrowest interval?
Required annotation format: set "annotation" to the selected interval's lower-to-upper segment as [[x0,y0],[x1,y1]].
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":[[310,268],[610,268]],"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / second_narrowest_interval_label / answer_only / sample 5497961587865673

- `instance_seed`: `5497961587865673`
- `word_count`: `40`
- `body_word_count`: `23`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. Which category has the second narrowest interval?
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / second_widest_interval_label / answer_and_annotation / sample 1874195493940495

- `instance_seed`: `1874195493940495`
- `word_count`: `58`
- `body_word_count`: `22`

```text
The image shows a bar chart with error bars, labeled categories, and printed interval endpoints. Which category has the second widest interval?
Annotation format: set "annotation" to the selected interval's lower-to-upper segment as [[x0,y0],[x1,y1]].
Answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":[[310,268],[610,268]],"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / second_widest_interval_label / answer_only / sample 1874195493940495

- `instance_seed`: `1874195493940495`
- `word_count`: `39`
- `body_word_count`: `22`

```text
The image shows a bar chart with error bars, labeled categories, and printed interval endpoints. Which category has the second widest interval?
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / widest_interval_label / answer_and_annotation / sample 5726937334019174

- `instance_seed`: `5726937334019174`
- `word_count`: `59`
- `body_word_count`: `21`

```text
The image shows a bar chart with error bars, labeled categories, and printed interval endpoints. Which category has the widest interval?
Required annotation format: set "annotation" to the selected interval's lower-to-upper segment as [[x0,y0],[x1,y1]].
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":[[310,268],[610,268]],"answer":"Cedar"}
```

### task_charts__error_interval__interval_width_rank_label / widest_interval_label / answer_only / sample 5726937334019174

- `instance_seed`: `5726937334019174`
- `word_count`: `38`
- `body_word_count`: `21`

```text
The image shows a bar chart with error bars, labeled categories, and printed interval endpoints. Which category has the widest interval?
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__error_interval__reference_containment_count / single / answer_and_annotation / sample 2993640493806102

- `instance_seed`: `2993640493806102`
- `word_count`: `72`
- `body_word_count`: `24`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. How many category intervals include reference value 52?
Annotation format: set "annotation" to an array of lower-to-upper interval segments, each segment written as [[x0,y0],[x1,y1]] for every interval that satisfies the condition.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[300,276],[470,276]],[[310,446],[520,446]]],"answer":2}
```

### task_charts__error_interval__reference_containment_count / single / answer_only / sample 2993640493806102

- `instance_seed`: `2993640493806102`
- `word_count`: `40`
- `body_word_count`: `24`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. How many category intervals include reference value 52?
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_charts__error_interval__reference_exclusion_side_count / entirely_above_reference_count / answer_and_annotation / sample 6546593430237440

- `instance_seed`: `6546593430237440`
- `word_count`: `75`
- `body_word_count`: `25`

```text
The image shows a vertical dot-and-whisker interval chart with labeled categories and printed interval endpoints. How many displayed intervals exclude 49 on the high side?
Required annotation format: set "annotation" to an array of lower-to-upper interval segments, each segment written as [[x0,y0],[x1,y1]] for every interval that satisfies the condition.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[300,276],[470,276]],[[310,446],[520,446]]],"answer":2}
```

### task_charts__error_interval__reference_exclusion_side_count / entirely_above_reference_count / answer_only / sample 6546593430237440

- `instance_seed`: `6546593430237440`
- `word_count`: `39`
- `body_word_count`: `25`

```text
The image shows a vertical dot-and-whisker interval chart with labeled categories and printed interval endpoints. How many displayed intervals exclude 49 on the high side?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_charts__error_interval__reference_exclusion_side_count / entirely_below_reference_count / answer_and_annotation / sample 2664811966024574

- `instance_seed`: `2664811966024574`
- `word_count`: `82`
- `body_word_count`: `28`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. For reference value 46, how many interval whiskers lie completely below it?
Format for the "annotation" field: set "annotation" to an array of lower-to-upper interval segments, each segment written as [[x0,y0],[x1,y1]] for every interval that satisfies the condition.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[300,276],[470,276]],[[310,446],[520,446]]],"answer":2}
```

### task_charts__error_interval__reference_exclusion_side_count / entirely_below_reference_count / answer_only / sample 2664811966024574

- `instance_seed`: `2664811966024574`
- `word_count`: `42`
- `body_word_count`: `28`

```text
The image shows a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers. For reference value 46, how many interval whiskers lie completely below it?
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_charts__errorbar_series__bound_extremum_x_label / highest_upper_bound_x_label / answer_and_annotation / sample 2882000023281358

- `instance_seed`: `2882000023281358`
- `word_count`: `68`
- `body_word_count`: `31`

```text
The image shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. For series "28Q1", which x-axis label has the highest upper error-bar endpoint?
Required annotation format: set "annotation" to the [x,y] pixel point on the selected error-bar endpoint.
Required answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[612,188],"answer":"FY24"}
```

### task_charts__errorbar_series__bound_extremum_x_label / highest_upper_bound_x_label / answer_only / sample 2882000023281358

- `instance_seed`: `2882000023281358`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The image shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. For series "28Q1", which x-axis label has the highest upper error-bar endpoint?
Final answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"FY24"}
```

### task_charts__errorbar_series__bound_extremum_x_label / lowest_lower_bound_x_label / answer_and_annotation / sample 5050385912296716

- `instance_seed`: `5050385912296716`
- `word_count`: `68`
- `body_word_count`: `31`

```text
The image shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. For series "Carmille", which x-axis label has the lowest lower error-bar endpoint?
Required annotation format: set "annotation" to the [x,y] pixel point on the selected error-bar endpoint.
Required answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[612,188],"answer":"FY24"}
```

### task_charts__errorbar_series__bound_extremum_x_label / lowest_lower_bound_x_label / answer_only / sample 5050385912296716

- `instance_seed`: `5050385912296716`
- `word_count`: `48`
- `body_word_count`: `31`

```text
The image shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. For series "Carmille", which x-axis label has the lowest lower error-bar endpoint?
Answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"FY24"}
```

### task_charts__errorbar_series__same_x_interval_overlap_count / single / answer_and_annotation / sample 7705857707812179

- `instance_seed`: `7705857707812179`
- `word_count`: `86`
- `body_word_count`: `33`

```text
The chart shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. At "Aeiden", count the other series whose error-bar interval overlaps the interval for "Roofers".
Format for the "annotation" field: set "annotation" to an array of lower-to-upper error-bar interval segments for the counted overlapping marks, each segment written as [[x0,y0],[x1,y1]].
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[[548,390],[548,300]],[[576,372],[576,282]]],"answer":2}
```

### task_charts__errorbar_series__same_x_interval_overlap_count / single / answer_only / sample 7705857707812179

- `instance_seed`: `7705857707812179`
- `word_count`: `46`
- `body_word_count`: `42`

```text
The chart shows a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars. At "Aeiden", count the other series whose error-bar interval overlaps the interval for "Roofers".
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_charts__heatmap__axis_cell_extremum_label / column_coolest_row_label / answer_and_annotation / sample 2408640662509827

- `instance_seed`: `2408640662509827`
- `word_count`: `83`
- `body_word_count`: `42`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. In column "Fri", which row label has the lowest-activity cell? If the requested label or color condition is not visible, answer exactly "unanswerable".
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected target cell.
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[400,163,440,203],"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / column_coolest_row_label / answer_only / sample 2408640662509827

- `instance_seed`: `2408640662509827`
- `word_count`: `61`
- `body_word_count`: `42`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. In column "Fri", which row label has the lowest-activity cell? If the requested label or color condition is not visible, answer exactly "unanswerable".
Answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / column_hottest_row_label / answer_and_annotation / sample 666839719126468

- `instance_seed`: `666839719126468`
- `word_count`: `83`
- `body_word_count`: `42`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. What row label has the highest-activity cell in column "Bilbao"? If the requested label or color condition is not visible, answer exactly "unanswerable".
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected target cell.
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[400,163,440,203],"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / column_hottest_row_label / answer_only / sample 666839719126468

- `instance_seed`: `666839719126468`
- `word_count`: `64`
- `body_word_count`: `42`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. What row label has the highest-activity cell in column "Bilbao"? If the requested label or color condition is not visible, answer exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / row_coolest_column_label / answer_and_annotation / sample 7617492959072194

- `instance_seed`: `7617492959072194`
- `word_count`: `92`
- `body_word_count`: `45`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. Look only at row "Week 1". What column label contains the lowest-activity cell? If the requested label or color condition is not visible, answer exactly "unanswerable".
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected target cell.
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[400,163,440,203],"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / row_coolest_column_label / answer_only / sample 7617492959072194

- `instance_seed`: `7617492959072194`
- `word_count`: `64`
- `body_word_count`: `45`

```text
The chart shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. Look only at row "Week 1". What column label contains the lowest-activity cell? If the requested label or color condition is not visible, answer exactly "unanswerable".
Answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / row_hottest_column_label / answer_and_annotation / sample 1559779283525708

- `instance_seed`: `1559779283525708`
- `word_count`: `90`
- `body_word_count`: `43`

```text
The image shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. What column label has the highest-activity cell in row "Week 4"? If the requested label or color condition is not visible, answer exactly "unanswerable".
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected target cell.
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[400,163,440,203],"answer":"Orly"}
```

### task_charts__heatmap__axis_cell_extremum_label / row_hottest_column_label / answer_only / sample 1559779283525708

- `instance_seed`: `1559779283525708`
- `word_count`: `63`
- `body_word_count`: `43`

```text
The image shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. What column label has the highest-activity cell in row "Week 4"? If the requested label or color condition is not visible, answer exactly "unanswerable".
Required answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Orly"}
```

### task_charts__heatmap__axis_condition_extremum_label / column_condition_extremum_label / answer_and_annotation / sample 3746503352041107

- `instance_seed`: `3746503352041107`
- `word_count`: `88`
- `body_word_count`: `31`

```text
The image shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. Which column label has the most cells with the highest activity level?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each matching cell in the winning row or column.
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[220,167,260,207],[346,167,386,207],[472,167,512,207]],"answer":"Cedar"}
```

### task_charts__heatmap__axis_condition_extremum_label / column_condition_extremum_label / answer_only / sample 3746503352041107

- `instance_seed`: `3746503352041107`
- `word_count`: `53`
- `body_word_count`: `31`

```text
The image shows a week-by-week calendar grid where darker colors indicate higher activity and lighter colors indicate lower activity. Which column label has the most cells with the highest activity level?
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__heatmap__axis_condition_extremum_label / row_condition_extremum_label / answer_and_annotation / sample 3665655598101347

- `instance_seed`: `3665655598101347`
- `word_count`: `90`
- `body_word_count`: `33`

```text
The image shows labeled grid cells where darker colors indicate higher intensity and lighter colors indicate lower intensity. What row label corresponds to the greatest count of cells with the lowest intensity level?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each matching cell in the winning row or column.
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[220,167,260,207],[346,167,386,207],[472,167,512,207]],"answer":"Cedar"}
```

### task_charts__heatmap__axis_condition_extremum_label / row_condition_extremum_label / answer_only / sample 3665655598101347

- `instance_seed`: `3665655598101347`
- `word_count`: `53`
- `body_word_count`: `33`

```text
The image shows labeled grid cells where darker colors indicate higher intensity and lighter colors indicate lower intensity. What row label corresponds to the greatest count of cells with the lowest intensity level?
Required answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"Cedar"}
```

### task_charts__heatmap__colorbar_interval_cell_count / single / answer_and_annotation / sample 5540712644985415

- `instance_seed`: `5540712644985415`
- `word_count`: `75`
- `body_word_count`: `27`

```text
The chart shows labeled grid cells colored by a continuous numeric colorbar scale. Using the colorbar scale, how many cells have values from 80 to 100, inclusive?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around all counted cells, in row-major order.
Required answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[400,163,440,203],[400,223,440,263]],"answer":2}
```

### task_charts__heatmap__colorbar_interval_cell_count / single / answer_only / sample 5540712644985415

- `instance_seed`: `5540712644985415`
- `word_count`: `46`
- `body_word_count`: `27`

```text
The chart shows labeled grid cells colored by a continuous numeric colorbar scale. Using the colorbar scale, how many cells have values from 80 to 100, inclusive?
Format for the "answer" field: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__heatmap__colorbar_threshold_cell_count / colorbar_above_threshold_cell_count / answer_and_annotation / sample 6564650333472919

- `instance_seed`: `6564650333472919`
- `word_count`: `77`
- `body_word_count`: `25`

```text
The chart shows labeled grid cells colored by a continuous numeric colorbar scale. How many heatmap cells are above 60 according to the colorbar scale?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around all counted cells, in row-major order.
Required answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[220,167,260,207],[346,167,386,207],[472,167,512,207]],"answer":3}
```

### task_charts__heatmap__colorbar_threshold_cell_count / colorbar_above_threshold_cell_count / answer_only / sample 6564650333472919

- `instance_seed`: `6564650333472919`
- `word_count`: `42`
- `body_word_count`: `25`

```text
The chart shows labeled grid cells colored by a continuous numeric colorbar scale. How many heatmap cells are above 60 according to the colorbar scale?
Final answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__heatmap__colorbar_threshold_cell_count / colorbar_below_threshold_cell_count / answer_and_annotation / sample 8348294420607877

- `instance_seed`: `8348294420607877`
- `word_count`: `75`
- `body_word_count`: `24`

```text
The image shows labeled grid cells colored by a continuous numeric colorbar scale. Using the colorbar scale, how many cells have values below 40?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around all counted cells, in row-major order.
Final answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[220,167,260,207],[346,167,386,207],[472,167,512,207]],"answer":3}
```

### task_charts__heatmap__colorbar_threshold_cell_count / colorbar_below_threshold_cell_count / answer_only / sample 8348294420607877

- `instance_seed`: `8348294420607877`
- `word_count`: `41`
- `body_word_count`: `24`

```text
The image shows labeled grid cells colored by a continuous numeric colorbar scale. Using the colorbar scale, how many cells have values below 40?
Final answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__heatmap__condition_run_extremum_label / single / answer_and_annotation / sample 8608938182619443

- `instance_seed`: `8608938182619443`
- `word_count`: `87`
- `body_word_count`: `33`

```text
The image shows labeled grid cells where darker colors indicate higher intensity and lighter colors indicate lower intensity. Which row label has the longest consecutive run of cells with the lowest intensity level?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the winning consecutive run cells, from left to right.
Answer field: set "answer" to the exact visible row label as a string.
Example JSON:
{"annotation":[[530,427,570,467],[593,427,633,467],[656,427,696,467]],"answer":"Mesa"}
```

### task_charts__heatmap__condition_run_extremum_label / single / answer_only / sample 8608938182619443

- `instance_seed`: `8608938182619443`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The image shows labeled grid cells where darker colors indicate higher intensity and lighter colors indicate lower intensity. Which row label has the longest consecutive run of cells with the lowest intensity level?
Answer field: set "answer" to the exact visible row label as a string.
Example JSON:
{"answer":"Mesa"}
```

### task_charts__hexbin_density__threshold_bin_count / above_threshold_bin_count / answer_and_annotation / sample 4447233350369313

- `instance_seed`: `4447233350369313`
- `word_count`: `70`
- `body_word_count`: `26`

```text
The chart shows a hexbin density chart with numeric axes and a discrete density-level legend. How many visible hex bins have density level at least 2?
Annotation format: set "annotation" to an array of [x,y] pixel points at the center of every visible hex bin matching the density-level threshold.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[234,204],[324,264]],"answer":2}
```

### task_charts__hexbin_density__threshold_bin_count / above_threshold_bin_count / answer_only / sample 4447233350369313

- `instance_seed`: `4447233350369313`
- `word_count`: `44`
- `body_word_count`: `26`

```text
The chart shows a hexbin density chart with numeric axes and a discrete density-level legend. How many visible hex bins have density level at least 2?
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__hexbin_density__threshold_bin_count / below_threshold_bin_count / answer_and_annotation / sample 7838085925009104

- `instance_seed`: `7838085925009104`
- `word_count`: `70`
- `body_word_count`: `26`

```text
The image shows a hexbin density chart with numeric axes and a discrete density-level legend. Count the visible hex bins whose density level is below 4.
Annotation format: set "annotation" to an array of [x,y] pixel points at the center of every visible hex bin matching the density-level threshold.
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[234,204],[324,264]],"answer":2}
```

### task_charts__hexbin_density__threshold_bin_count / below_threshold_bin_count / answer_only / sample 7838085925009104

- `instance_seed`: `7838085925009104`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The image shows a hexbin density chart with numeric axes and a discrete density-level legend. Count the visible hex bins whose density level is below 4.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__histogram__cumulative_rank_bin_label / single / answer_and_annotation / sample 7421877514657465

- `instance_seed`: `7421877514657465`
- `word_count`: `78`
- `body_word_count`: `31`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. Number the counted items from left to right across the histogram. Which x-axis value contains item 140?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] box around the answer histogram bar.
Format for the "answer" field: set "answer" to the x-axis value containing the requested item rank, as an integer.
Example JSON:
{"annotation":[336,240,372,520],"answer":18}
```

### task_charts__histogram__cumulative_rank_bin_label / single / answer_only / sample 7421877514657465

- `instance_seed`: `7421877514657465`
- `word_count`: `52`
- `body_word_count`: `31`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. Number the counted items from left to right across the histogram. Which x-axis value contains item 140?
Final answer format: set "answer" to the x-axis value containing the requested item rank, as an integer.
Example JSON:
{"answer":18}
```

### task_charts__histogram__interval_mass / inside_interval_mass / answer_and_annotation / sample 8454983653653560

- `instance_seed`: `8454983653653560`
- `word_count`: `71`
- `body_word_count`: `24`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. What is the total count inside the value interval "24-38"?
Final answer format: set "answer" to the requested total count as an integer.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around the histogram bars included in the total.
Example JSON:
{"annotation":[[210,320,246,520],[252,280,288,520]],"answer":17}
```

### task_charts__histogram__interval_mass / inside_interval_mass / answer_only / sample 8454983653653560

- `instance_seed`: `8454983653653560`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. What is the total count inside the value interval "24-38"?
Answer field: set "answer" to the requested total count as an integer.
Example JSON:
{"answer":17}
```

### task_charts__histogram__interval_mass / outside_interval_mass / answer_and_annotation / sample 6083453317326745

- `instance_seed`: `6083453317326745`
- `word_count`: `71`
- `body_word_count`: `24`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. What is the total count outside the value interval "39-46"?
Final answer format: set "answer" to the requested total count as an integer.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around the histogram bars included in the total.
Example JSON:
{"annotation":[[210,320,246,520],[252,280,288,520]],"answer":17}
```

### task_charts__histogram__interval_mass / outside_interval_mass / answer_only / sample 6083453317326745

- `instance_seed`: `6083453317326745`
- `word_count`: `43`
- `body_word_count`: `24`

```text
The image shows a histogram with labeled x-axis values and bar heights showing counts. What is the total count outside the value interval "39-46"?
Format for the "answer" field: set "answer" to the requested total count as an integer.
Example JSON:
{"answer":17}
```

### task_charts__matrix__axis_extremum_label / column_highest_axis_extremum_label / answer_and_annotation / sample 6769476069101709

- `instance_seed`: `6769476069101709`
- `word_count`: `100`
- `body_word_count`: `38`

```text
The figure shows a labeled triangular pairwise matrix where only the filled cells count. In column "CDGLF", which row label has the second-highest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for all candidate cells in the selected row or column.
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[240,300,310,345],[320,300,390,345],[400,300,470,345]],"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / column_highest_axis_extremum_label / answer_only / sample 6769476069101709

- `instance_seed`: `6769476069101709`
- `word_count`: `58`
- `body_word_count`: `38`

```text
The figure shows a labeled triangular pairwise matrix where only the filled cells count. In column "CDGLF", which row label has the second-highest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Final answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / column_lowest_axis_extremum_label / answer_and_annotation / sample 1148800707456799

- `instance_seed`: `1148800707456799`
- `word_count`: `99`
- `body_word_count`: `42`

```text
The image shows a labeled confusion matrix with printed integer counts in each active cell. For column "23Q3", what row label has the cell with the second-lowest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for all candidate cells in the selected row or column.
Final answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[240,300,310,345],[320,300,390,345],[400,300,470,345]],"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / column_lowest_axis_extremum_label / answer_only / sample 1148800707456799

- `instance_seed`: `1148800707456799`
- `word_count`: `61`
- `body_word_count`: `57`

```text
The image shows a labeled confusion matrix with printed integer counts in each active cell. For column "23Q3", what row label has the cell with the second-lowest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / row_highest_axis_extremum_label / answer_and_annotation / sample 1771124583331139

- `instance_seed`: `1771124583331139`
- `word_count`: `97`
- `body_word_count`: `39`

```text
The visual shows a labeled triangular pairwise matrix where only the filled cells count. Within the row labeled "Zambia", which column has the second-highest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for all candidate cells in the selected row or column.
Required answer format: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[240,300,310,345],[320,300,390,345],[400,300,470,345]],"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / row_highest_axis_extremum_label / answer_only / sample 1771124583331139

- `instance_seed`: `1771124583331139`
- `word_count`: `58`
- `body_word_count`: `54`

```text
The visual shows a labeled triangular pairwise matrix where only the filled cells count. Within the row labeled "Zambia", which column has the second-highest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Answer field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / row_lowest_axis_extremum_label / answer_and_annotation / sample 3302899782955150

- `instance_seed`: `3302899782955150`
- `word_count`: `102`
- `body_word_count`: `40`

```text
The image shows a labeled annotated heatmap table with printed integer values in each cell. Within the row labeled "Dyonte", which column has the second-lowest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for all candidate cells in the selected row or column.
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"annotation":[[240,300,310,345],[320,300,390,345],[400,300,470,345]],"answer":"C7"}
```

### task_charts__matrix__axis_extremum_label / row_lowest_axis_extremum_label / answer_only / sample 3302899782955150

- `instance_seed`: `3302899782955150`
- `word_count`: `62`
- `body_word_count`: `40`

```text
The image shows a labeled annotated heatmap table with printed integer values in each cell. Within the row labeled "Dyonte", which column has the second-lowest printed value? If the requested row or column label is not visible, answer exactly "unanswerable".
Format for the "answer" field: set "answer" to the exact visible row or column label as a string.
Example JSON:
{"answer":"C7"}
```

### task_charts__matrix__off_diagonal_confusion_label / single / answer_and_annotation / sample 8047777037323046

- `instance_seed`: `8047777037323046`
- `word_count`: `91`
- `body_word_count`: `35`

```text
The image shows a labeled confusion matrix with printed integer counts in each active cell. In the row for actual class "Imina", exclude the matching diagonal cell. What predicted column label has the largest count?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the off-diagonal candidate cells in the actual-class row.
Required answer format: set "answer" to the exact visible predicted column label as a string.
Example JSON:
{"annotation":[[240,260,310,305],[320,260,390,305],[400,260,470,305]],"answer":"C5"}
```

### task_charts__matrix__off_diagonal_confusion_label / single / answer_only / sample 8047777037323046

- `instance_seed`: `8047777037323046`
- `word_count`: `56`
- `body_word_count`: `35`

```text
The image shows a labeled confusion matrix with printed integer counts in each active cell. In the row for actual class "Imina", exclude the matching diagonal cell. What predicted column label has the largest count?
Format for the "answer" field: set "answer" to the exact visible predicted column label as a string.
Example JSON:
{"answer":"C5"}
```

### task_charts__matrix__threshold_cell_count / column_at_least_threshold_cell_count / answer_and_annotation / sample 8375620422785198

- `instance_seed`: `8375620422785198`
- `word_count`: `86`
- `body_word_count`: `27`

```text
The chart shows a labeled triangular pairwise matrix where only the filled cells count. Count the cells in column "Plus" whose printed values are at least 26.
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the cells matching the threshold.
Format for the "answer" field: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[240,260,310,305],[320,260,390,305],[400,260,470,305],[480,260,550,305]],"answer":4}
```

### task_charts__matrix__threshold_cell_count / column_at_least_threshold_cell_count / answer_only / sample 8375620422785198

- `instance_seed`: `8375620422785198`
- `word_count`: `46`
- `body_word_count`: `27`

```text
The chart shows a labeled triangular pairwise matrix where only the filled cells count. Count the cells in column "Plus" whose printed values are at least 26.
Format for the "answer" field: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":4}
```

### task_charts__matrix__threshold_cell_count / column_at_most_threshold_cell_count / answer_and_annotation / sample 2620320035513289

- `instance_seed`: `2620320035513289`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The visual shows a labeled annotated heatmap table with printed integer values in each cell. Look only at column "Fontana". Count the active cells with values at most 30.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the cells matching the threshold.
Final answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[240,260,310,305],[320,260,390,305],[400,260,470,305],[480,260,550,305]],"answer":4}
```

### task_charts__matrix__threshold_cell_count / column_at_most_threshold_cell_count / answer_only / sample 2620320035513289

- `instance_seed`: `2620320035513289`
- `word_count`: `46`
- `body_word_count`: `29`

```text
The visual shows a labeled annotated heatmap table with printed integer values in each cell. Look only at column "Fontana". Count the active cells with values at most 30.
Required answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":4}
```

### task_charts__matrix__threshold_cell_count / row_at_least_threshold_cell_count / answer_and_annotation / sample 5539916880669041

- `instance_seed`: `5539916880669041`
- `word_count`: `80`
- `body_word_count`: `27`

```text
The chart shows a labeled triangular pairwise matrix where only the filled cells count. In row "Core", how many active cells have printed values at least 24?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the cells matching the threshold.
Answer field: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[240,260,310,305],[320,260,390,305],[400,260,470,305],[480,260,550,305]],"answer":4}
```

### task_charts__matrix__threshold_cell_count / row_at_least_threshold_cell_count / answer_only / sample 5539916880669041

- `instance_seed`: `5539916880669041`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The chart shows a labeled triangular pairwise matrix where only the filled cells count. In row "Core", how many active cells have printed values at least 24?
Required answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":4}
```

### task_charts__matrix__threshold_cell_count / row_at_most_threshold_cell_count / answer_and_annotation / sample 3699385601604910

- `instance_seed`: `3699385601604910`
- `word_count`: `80`
- `body_word_count`: `26`

```text
The image shows a labeled annotated heatmap table with printed integer values in each cell. For row "Seagle", how many printed values are at most 56?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the cells matching the threshold.
Final answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"annotation":[[240,260,310,305],[320,260,390,305],[400,260,470,305],[480,260,550,305]],"answer":4}
```

### task_charts__matrix__threshold_cell_count / row_at_most_threshold_cell_count / answer_only / sample 3699385601604910

- `instance_seed`: `3699385601604910`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The image shows a labeled annotated heatmap table with printed integer values in each cell. For row "Seagle", how many printed values are at most 56?
Required answer format: set "answer" to the requested cell count as an integer.
Example JSON:
{"answer":4}
```

### task_charts__multiseries__category_total_extremum_label / largest_category_total_label / answer_and_annotation / sample 3559964209461014

- `instance_seed`: `3559964209461014`
- `word_count`: `100`
- `body_word_count`: `43`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. For each category, add all series values. Which category has the largest total?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark in the answer category.
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,220],"K4M8:Vega":[300,310],"K4M8:Tana":[300,390]},"answer":"K4M8"}
```

### task_charts__multiseries__category_total_extremum_label / largest_category_total_label / answer_only / sample 3559964209461014

- `instance_seed`: `3559964209461014`
- `word_count`: `60`
- `body_word_count`: `43`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. For each category, add all series values. Which category has the largest total?
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__category_total_extremum_label / smallest_category_total_label / answer_and_annotation / sample 6087282813620185

- `instance_seed`: `6087282813620185`
- `word_count`: `96`
- `body_word_count`: `40`

```text
The image shows a grouped lollipop chart with labeled categories on the horizontal axis and a legend. Each colored point gives that series value for its category. Across the labeled categories, which one has the smallest sum over all series?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark in the answer category.
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,220],"K4M8:Vega":[300,310],"K4M8:Tana":[300,390]},"answer":"K4M8"}
```

### task_charts__multiseries__category_total_extremum_label / smallest_category_total_label / answer_only / sample 6087282813620185

- `instance_seed`: `6087282813620185`
- `word_count`: `56`
- `body_word_count`: `52`

```text
The image shows a grouped lollipop chart with labeled categories on the horizontal axis and a legend. Each colored point gives that series value for its category. Across the labeled categories, which one has the smallest sum over all series?
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__pair_equality_label / single / answer_and_annotation / sample 4290792736264930

- `instance_seed`: `4290792736264930`
- `word_count`: `103`
- `body_word_count`: `47`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Use the legend to compare "Evo" and "Roof". Which category has equal values for them?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the two equal-valued queried series marks in the answer category.
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"M7P2:Orly":[260,240],"M7P2:Vega":[260,240]},"answer":"M7P2"}
```

### task_charts__multiseries__pair_equality_label / single / answer_only / sample 4290792736264930

- `instance_seed`: `4290792736264930`
- `word_count`: `64`
- `body_word_count`: `47`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Use the legend to compare "Evo" and "Roof". Which category has equal values for them?
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"M7P2"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_absolute_gap_label / answer_and_annotation / sample 3284077111208049

- `instance_seed`: `3284077111208049`
- `word_count`: `99`
- `body_word_count`: `46`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Find the category where the absolute difference between "Spac" and "Land" is the largest.
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's two queried series marks.
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"M7P2:Orly":[260,340],"M7P2:Vega":[260,160]},"answer":"M7P2"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_absolute_gap_label / answer_only / sample 3284077111208049

- `instance_seed`: `3284077111208049`
- `word_count`: `62`
- `body_word_count`: `58`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Find the category where the absolute difference between "Spac" and "Land" is the largest.
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"M7P2"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_decrease_label / answer_and_annotation / sample 2894590821008615

- `instance_seed`: `2894590821008615`
- `word_count`: `95`
- `body_word_count`: `41`

```text
The figure shows a grouped lollipop chart with labeled categories on the horizontal axis and a legend. Each colored point gives that series value for its category. Determine the category label with the largest decrease when moving from "Week" to "Tapp".
Required annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's two queried series marks.
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[260,320],"K4M8:Vega":[260,180]},"answer":"K4M8"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_decrease_label / answer_only / sample 2894590821008615

- `instance_seed`: `2894590821008615`
- `word_count`: `60`
- `body_word_count`: `41`

```text
The figure shows a grouped lollipop chart with labeled categories on the horizontal axis and a legend. Each colored point gives that series value for its category. Determine the category label with the largest decrease when moving from "Week" to "Tapp".
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_increase_label / answer_and_annotation / sample 7086618947572522

- `instance_seed`: `7086618947572522`
- `word_count`: `99`
- `body_word_count`: `47`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Compare "Luan" and "Copp" for each category. Which category has the largest increase from first to second?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's two queried series marks.
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[260,320],"K4M8:Vega":[260,180]},"answer":"K4M8"}
```

### task_charts__multiseries__ranked_change_extremum_label / largest_increase_label / answer_only / sample 7086618947572522

- `instance_seed`: `7086618947572522`
- `word_count`: `63`
- `body_word_count`: `59`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Compare "Luan" and "Copp" for each category. Which category has the largest increase from first to second?
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__ranked_change_extremum_label / smallest_absolute_gap_label / answer_and_annotation / sample 7862840672322324

- `instance_seed`: `7862840672322324`
- `word_count`: `104`
- `body_word_count`: `46`

```text
The figure shows a grouped bar chart with labeled category groups on the horizontal axis and a legend. Each colored bar height gives that series value for its category. Compare "Luga" and "Miri" for each category. Which category has the smallest requested distance between their values?
Format for the "annotation" field: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's two queried series marks.
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"M7P2:Orly":[260,340],"M7P2:Vega":[260,160]},"answer":"M7P2"}
```

### task_charts__multiseries__ranked_change_extremum_label / smallest_absolute_gap_label / answer_only / sample 7862840672322324

- `instance_seed`: `7862840672322324`
- `word_count`: `65`
- `body_word_count`: `46`

```text
The figure shows a grouped bar chart with labeled category groups on the horizontal axis and a legend. Each colored bar height gives that series value for its category. Compare "Luga" and "Miri" for each category. Which category has the smallest requested distance between their values?
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"M7P2"}
```

### task_charts__multiseries__ranked_pair_ratio_extremum_label / largest_pair_ratio_label / answer_and_annotation / sample 1503097537834314

- `instance_seed`: `1503097537834314`
- `word_count`: `103`
- `body_word_count`: `49`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Use the legend to read "Xaia" and "Sya" for each category. Which category has the largest ratio?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's numerator and denominator series marks.
Final answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"M7P2:Orly":[300,180],"M7P2:Vega":[300,300]},"answer":"M7P2"}
```

### task_charts__multiseries__ranked_pair_ratio_extremum_label / largest_pair_ratio_label / answer_only / sample 1503097537834314

- `instance_seed`: `1503097537834314`
- `word_count`: `68`
- `body_word_count`: `49`

```text
The image shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Use the legend to read "Xaia" and "Sya" for each category. Which category has the largest ratio?
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"M7P2"}
```

### task_charts__multiseries__ranked_pair_ratio_extremum_label / smallest_pair_ratio_label / answer_and_annotation / sample 4541752389693992

- `instance_seed`: `4541752389693992`
- `word_count`: `96`
- `body_word_count`: `43`

```text
The figure shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. For each category, divide "Mese" by "Debo". Which category has the smallest ratio?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for the answer category's numerator and denominator series marks.
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"M7P2:Orly":[300,180],"M7P2:Vega":[300,300]},"answer":"M7P2"}
```

### task_charts__multiseries__ranked_pair_ratio_extremum_label / smallest_pair_ratio_label / answer_only / sample 4541752389693992

- `instance_seed`: `4541752389693992`
- `word_count`: `60`
- `body_word_count`: `43`

```text
The figure shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. For each category, divide "Mese" by "Debo". Which category has the smallest ratio?
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"M7P2"}
```

### task_charts__multiseries__ranked_series_share_extremum_label / largest_series_share_label / answer_and_annotation / sample 7273718880400616

- `instance_seed`: `7273718880400616`
- `word_count`: `108`
- `body_word_count`: `50`

```text
The visual shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Which category label has the largest percentage share for "Sika" out of that category's total across all series?
Required annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark in the answer category.
Required answer format: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,240],"K4M8:Vega":[300,320],"K4M8:Tana":[300,400]},"answer":"K4M8"}
```

### task_charts__multiseries__ranked_series_share_extremum_label / largest_series_share_label / answer_only / sample 7273718880400616

- `instance_seed`: `7273718880400616`
- `word_count`: `66`
- `body_word_count`: `50`

```text
The visual shows a multi-line chart with labeled categories on the horizontal axis and a legend. Each colored series has one point per category, and the relevant values are the points' y-values. Which category label has the largest percentage share for "Sika" out of that category's total across all series?
Answer format: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__ranked_series_share_extremum_label / smallest_series_share_label / answer_and_annotation / sample 5688767160430220

- `instance_seed`: `5688767160430220`
- `word_count`: `110`
- `body_word_count`: `48`

```text
The figure shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Which category label has the smallest percentage share for "Onl" out of that category's total across all series?
Format for the "annotation" field: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark in the answer category.
Format for the "answer" field: set "answer" to the requested category label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,240],"K4M8:Vega":[300,320],"K4M8:Tana":[300,400]},"answer":"K4M8"}
```

### task_charts__multiseries__ranked_series_share_extremum_label / smallest_series_share_label / answer_only / sample 5688767160430220

- `instance_seed`: `5688767160430220`
- `word_count`: `64`
- `body_word_count`: `60`

```text
The figure shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Which category label has the smallest percentage share for "Onl" out of that category's total across all series?
Answer field: set "answer" to the requested category label as a string.
Example JSON:
{"answer":"K4M8"}
```

### task_charts__multiseries__series_rank_at_category_label / largest_series_at_category_label / answer_and_annotation / sample 5149194503754771

- `instance_seed`: `5149194503754771`
- `word_count`: `98`
- `body_word_count`: `41`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Within the category labeled "S4T5", which legend series is the largest?
Annotation format: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark at the queried category.
Answer field: set "answer" to the requested visible series label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,240],"K4M8:Vega":[300,320],"K4M8:Tana":[300,400]},"answer":"Vega"}
```

### task_charts__multiseries__series_rank_at_category_label / largest_series_at_category_label / answer_only / sample 5149194503754771

- `instance_seed`: `5149194503754771`
- `word_count`: `59`
- `body_word_count`: `41`

```text
The image shows a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. Each colored bar length gives that series value for its category. Within the category labeled "S4T5", which legend series is the largest?
Final answer format: set "answer" to the requested visible series label as a string.
Example JSON:
{"answer":"Vega"}
```

### task_charts__multiseries__series_rank_at_category_label / smallest_series_at_category_label / answer_and_annotation / sample 995715616103923

- `instance_seed`: `995715616103923`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The figure shows a grouped bar chart with labeled category groups on the horizontal axis and a legend. Each colored bar height gives that series value for its category. At category "Reda", which series has the smallest value?
Format for the "annotation" field: set "annotation" to an object mapping each "<category>:<series>" mark key to an [x,y] pixel point for every series mark at the queried category.
Format for the "answer" field: set "answer" to the requested visible series label as a string.
Example JSON:
{"annotation":{"K4M8:Orly":[300,240],"K4M8:Vega":[300,320],"K4M8:Tana":[300,400]},"answer":"Vega"}
```

### task_charts__multiseries__series_rank_at_category_label / smallest_series_at_category_label / answer_only / sample 995715616103923

- `instance_seed`: `995715616103923`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The figure shows a grouped bar chart with labeled category groups on the horizontal axis and a legend. Each colored bar height gives that series value for its category. At category "Reda", which series has the smallest value?
Final answer format: set "answer" to the requested visible series label as a string.
Example JSON:
{"answer":"Vega"}
```

### task_charts__parallel_coords__all_crossings_between_adjacent_axes / single / answer_and_annotation / sample 4481005657988542

- `instance_seed`: `4481005657988542`
- `word_count`: `88`
- `body_word_count`: `39`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many profile-line intersections are formed between "28Q3" and "28Q4"?
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points, one point at each counted line crossing between the two named axes.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[310,260],[420,340]],"answer":2}
```

### task_charts__parallel_coords__all_crossings_between_adjacent_axes / single / answer_only / sample 4481005657988542

- `instance_seed`: `4481005657988542`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many profile-line intersections are formed between "28Q3" and "28Q4"?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / above_on_both_axes / answer_and_annotation / sample 1668503285363549

- `instance_seed`: `1668503285363549`
- `word_count`: `99`
- `body_word_count`: `45`

```text
The chart shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Using highlighted adjacent axes "Reniel" and "Zeniya", how many profiles are above 8 on both axes?
Annotation format: set "annotation" to an array of line segments, one segment for each counted profile between the two named axes; each segment is [[x0,y0],[x1,y1]] in pixel coordinates.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[260,210],[430,250]],[[260,390],[430,330]]],"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / above_on_both_axes / answer_only / sample 1668503285363549

- `instance_seed`: `1668503285363549`
- `word_count`: `62`
- `body_word_count`: `45`

```text
The chart shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Using highlighted adjacent axes "Reniel" and "Zeniya", how many profiles are above 8 on both axes?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / above_on_one_below_on_other / answer_and_annotation / sample 2062685484524244

- `instance_seed`: `2062685484524244`
- `word_count`: `102`
- `body_word_count`: `46`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many labeled profiles cross from above 12 on "Irelynd" to below 12 on adjacent axis "Dewaun"?
Required annotation format: set "annotation" to an array of line segments, one segment for each counted profile between the two named axes; each segment is [[x0,y0],[x1,y1]] in pixel coordinates.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[260,210],[430,250]],[[260,390],[430,330]]],"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / above_on_one_below_on_other / answer_only / sample 2062685484524244

- `instance_seed`: `2062685484524244`
- `word_count`: `63`
- `body_word_count`: `46`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many labeled profiles cross from above 12 on "Irelynd" to below 12 on adjacent axis "Dewaun"?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / below_on_both_axes / answer_and_annotation / sample 3107229217730169

- `instance_seed`: `3107229217730169`
- `word_count`: `99`
- `body_word_count`: `45`

```text
The figure shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many labeled profiles sit below 11 on each of the adjacent axes "Elika" and "Keegon"?
Annotation format: set "annotation" to an array of line segments, one segment for each counted profile between the two named axes; each segment is [[x0,y0],[x1,y1]] in pixel coordinates.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[260,210],[430,250]],[[260,390],[430,330]]],"answer":2}
```

### task_charts__parallel_coords__axis_condition_count / below_on_both_axes / answer_only / sample 3107229217730169

- `instance_seed`: `3107229217730169`
- `word_count`: `59`
- `body_word_count`: `45`

```text
The figure shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. How many labeled profiles sit below 11 on each of the adjacent axes "Elika" and "Keegon"?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_absolute_change_between_axes / answer_and_annotation / sample 4977104356292264

- `instance_seed`: `4977104356292264`
- `word_count`: `87`
- `body_word_count`: `43`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which labeled profile has the greatest value difference between adjacent axes "Sunshine" and "Ventures"?
Annotation format: set "annotation" to the answer profile segment between the two named axes as [[x0,y0],[x1,y1]] in pixel coordinates.
Answer format: set "answer" to the exact visible profile label as a string.
Example JSON:
{"annotation":[[260,340],[430,180]],"answer":"K7"}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_absolute_change_between_axes / answer_only / sample 4977104356292264

- `instance_seed`: `4977104356292264`
- `word_count`: `61`
- `body_word_count`: `43`

```text
The visual shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which labeled profile has the greatest value difference between adjacent axes "Sunshine" and "Ventures"?
Final answer format: set "answer" to the exact visible profile label as a string.
Example JSON:
{"answer":"K7"}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_decrease_between_axes / answer_and_annotation / sample 3537856109055024

- `instance_seed`: `3537856109055024`
- `word_count`: `85`
- `body_word_count`: `41`

```text
The figure shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which profile has the largest decrease from "Ireland" to adjacent axis "Iraq"?
Annotation format: set "annotation" to the answer profile segment between the two named axes as [[x0,y0],[x1,y1]] in pixel coordinates.
Answer field: set "answer" to the exact visible profile label as a string.
Example JSON:
{"annotation":[[260,340],[430,180]],"answer":"K7"}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_decrease_between_axes / answer_only / sample 3537856109055024

- `instance_seed`: `3537856109055024`
- `word_count`: `58`
- `body_word_count`: `41`

```text
The figure shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which profile has the largest decrease from "Ireland" to adjacent axis "Iraq"?
Answer format: set "answer" to the exact visible profile label as a string.
Example JSON:
{"answer":"K7"}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_increase_between_axes / answer_and_annotation / sample 4904531986774119

- `instance_seed`: `4904531986774119`
- `word_count`: `93`
- `body_word_count`: `43`

```text
The image shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which labeled profile rises by the greatest amount between adjacent axes "Jul30" and "Aug06"?
Format for the "annotation" field: set "annotation" to the answer profile segment between the two named axes as [[x0,y0],[x1,y1]] in pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible profile label as a string.
Example JSON:
{"annotation":[[260,340],[430,180]],"answer":"K7"}
```

### task_charts__parallel_coords__axis_delta_extremum_label / largest_increase_between_axes / answer_only / sample 4904531986774119

- `instance_seed`: `4904531986774119`
- `word_count`: `63`
- `body_word_count`: `43`

```text
The image shows a parallel-coordinates chart. Each colored profile line is labeled at the ends and crosses the vertical metric axes; larger metric values are higher on each axis. Which labeled profile rises by the greatest amount between adjacent axes "Jul30" and "Aug06"?
Format for the "answer" field: set "answer" to the exact visible profile label as a string.
Example JSON:
{"answer":"K7"}
```

### task_charts__part_whole__adjacent_transfer_gap_value / clockwise_adjacent_transfer / answer_and_annotation / sample 2517366654837611

- `instance_seed`: `2517366654837611`
- `word_count`: `97`
- `body_word_count`: `39`

```text
The figure shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Tools" and target its immediate clockwise neighbor. After moving 8 points from source to target, what share gap remains?
Format for the "annotation" field: set "annotation" to an object mapping the source category label and adjacent target category label to [x,y] pixel points at the centers of their chart segments.
Format for the "answer" field: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"annotation":{"Ruby":[590,250],"Crimson":[740,380]},"answer":13}
```

### task_charts__part_whole__adjacent_transfer_gap_value / clockwise_adjacent_transfer / answer_only / sample 2517366654837611

- `instance_seed`: `2517366654837611`
- `word_count`: `55`
- `body_word_count`: `39`

```text
The figure shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Tools" and target its immediate clockwise neighbor. After moving 8 points from source to target, what share gap remains?
Answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"answer":13}
```

### task_charts__part_whole__adjacent_transfer_gap_value / counterclockwise_adjacent_transfer / answer_and_annotation / sample 1351893675659305

- `instance_seed`: `1351893675659305`
- `word_count`: `92`
- `body_word_count`: `39`

```text
The chart shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Flint" and target its immediate counterclockwise neighbor. After moving 5 points from source to target, what share gap remains?
Annotation format: set "annotation" to an object mapping the source category label and adjacent target category label to [x,y] pixel points at the centers of their chart segments.
Final answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"annotation":{"Ruby":[590,250],"Crimson":[740,380]},"answer":13}
```

### task_charts__part_whole__adjacent_transfer_gap_value / counterclockwise_adjacent_transfer / answer_only / sample 1351893675659305

- `instance_seed`: `1351893675659305`
- `word_count`: `55`
- `body_word_count`: `39`

```text
The chart shows one donut chart with a table of exact integer category shares. Around the chart, choose source category "Flint" and target its immediate counterclockwise neighbor. After moving 5 points from source to target, what share gap remains?
Answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"answer":13}
```

### task_charts__part_whole__contiguous_chart_order_sum / clockwise_span / answer_and_annotation / sample 6532092902434063

- `instance_seed`: `6532092902434063`
- `word_count`: `95`
- `body_word_count`: `33`

```text
The visual shows one pie chart with a table of exact integer category shares. Read the contiguous chart segment from "Software" to "Grocery" while moving clockwise. What is the sum of those shares?
Format for the "annotation" field: set "annotation" to an object mapping each included category label to the [x,y] pixel point at the center of its chart segment.
Format for the "answer" field: set "answer" to the requested integer share value; omit the percent sign.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472],"Dune":[518,436]},"answer":42}
```

### task_charts__part_whole__contiguous_chart_order_sum / clockwise_span / answer_only / sample 6532092902434063

- `instance_seed`: `6532092902434063`
- `word_count`: `54`
- `body_word_count`: `33`

```text
The visual shows one pie chart with a table of exact integer category shares. Read the contiguous chart segment from "Software" to "Grocery" while moving clockwise. What is the sum of those shares?
Format for the "answer" field: set "answer" to the requested integer share value; omit the percent sign.
Example JSON:
{"answer":42}
```

### task_charts__part_whole__contiguous_chart_order_sum / counterclockwise_span / answer_and_annotation / sample 520212617804615

- `instance_seed`: `520212617804615`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The figure shows one pie chart with a table of exact integer category shares. Read the contiguous chart segment from "Music" to "Beverage" while moving counterclockwise. What is the sum of those shares?
Annotation format: set "annotation" to an object mapping each included category label to the [x,y] pixel point at the center of its chart segment.
Answer field: set "answer" to the requested integer share value; omit the percent sign.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472],"Dune":[518,436]},"answer":42}
```

### task_charts__part_whole__contiguous_chart_order_sum / counterclockwise_span / answer_only / sample 520212617804615

- `instance_seed`: `520212617804615`
- `word_count`: `52`
- `body_word_count`: `33`

```text
The figure shows one pie chart with a table of exact integer category shares. Read the contiguous chart segment from "Music" to "Beverage" while moving counterclockwise. What is the sum of those shares?
Required answer format: set "answer" to the requested integer share value; omit the percent sign.
Example JSON:
{"answer":42}
```

### task_charts__part_whole__sector_share_to_angle / clockwise_sector_angle / answer_and_annotation / sample 2052361666976211

- `instance_seed`: `2052361666976211`
- `word_count`: `92`
- `body_word_count`: `33`

```text
The chart shows one pie chart with a table of exact integer category shares. Moving clockwise around the chart, what central angle in degrees is covered from category "Kitchen" through category "Pharmacy", inclusive?
Format for the "annotation" field: set "annotation" to an object mapping each included category label to the [x,y] pixel point at the center of its chart segment.
Format for the "answer" field: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472]},"answer":108}
```

### task_charts__part_whole__sector_share_to_angle / clockwise_sector_angle / answer_only / sample 2052361666976211

- `instance_seed`: `2052361666976211`
- `word_count`: `51`
- `body_word_count`: `33`

```text
The chart shows one pie chart with a table of exact integer category shares. Moving clockwise around the chart, what central angle in degrees is covered from category "Kitchen" through category "Pharmacy", inclusive?
Answer format: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"answer":108}
```

### task_charts__part_whole__sector_share_to_angle / counterclockwise_sector_angle / answer_and_annotation / sample 6890368762996980

- `instance_seed`: `6890368762996980`
- `word_count`: `90`
- `body_word_count`: `36`

```text
The image shows one donut chart with a table of exact integer category shares. Use the counterclockwise chart order. Convert the combined share from "Services" through "Cloud", including both endpoints, into a central angle in degrees.
Annotation format: set "annotation" to an object mapping each included category label to the [x,y] pixel point at the center of its chart segment.
Final answer format: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472]},"answer":108}
```

### task_charts__part_whole__sector_share_to_angle / counterclockwise_sector_angle / answer_only / sample 6890368762996980

- `instance_seed`: `6890368762996980`
- `word_count`: `54`
- `body_word_count`: `36`

```text
The image shows one donut chart with a table of exact integer category shares. Use the counterclockwise chart order. Convert the combined share from "Services" through "Cloud", including both endpoints, into a central angle in degrees.
Answer format: set "answer" to the requested central angle in degrees as an integer.
Example JSON:
{"answer":108}
```

### task_charts__part_whole__subset_denominator_share_value / single / answer_and_annotation / sample 2659241941561476

- `instance_seed`: `2659241941561476`
- `word_count`: `81`
- `body_word_count`: `29`

```text
The image shows one pie chart with a table of exact integer category shares. Treat categories "Ivory", "Ruby", "Cobalt" as 100% of the subset. What percentage is category "Ivory"?
Annotation format: set "annotation" to an object mapping each denominator-subset category label to the [x,y] pixel point at the center of its chart segment.
Answer field: set "answer" to the requested integer percentage; omit the percent sign.
Example JSON:
{"annotation":{"Aster":[565,236],"Birch":[716,314],"Cedar":[680,472]},"answer":40}
```

### task_charts__part_whole__subset_denominator_share_value / single / answer_only / sample 2659241941561476

- `instance_seed`: `2659241941561476`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The image shows one pie chart with a table of exact integer category shares. Treat categories "Ivory", "Ruby", "Cobalt" as 100% of the subset. What percentage is category "Ivory"?
Final answer format: set "answer" to the requested integer percentage; omit the percent sign.
Example JSON:
{"answer":40}
```

### task_charts__pictogram__category_total_extremum_label / largest_total_category_label / answer_and_annotation / sample 4024665597269586

- `instance_seed`: `4024665597269586`
- `word_count`: `75`
- `body_word_count`: `36`

```text
The image contains a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Compare all category totals represented in the pictogram. Which visible category row represents the largest total value?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the answer category row.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[92,180,860,248],"answer":"Orchid"}
```

### task_charts__pictogram__category_total_extremum_label / largest_total_category_label / answer_only / sample 4024665597269586

- `instance_seed`: `4024665597269586`
- `word_count`: `53`
- `body_word_count`: `49`

```text
The image contains a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Compare all category totals represented in the pictogram. Which visible category row represents the largest total value?
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__pictogram__category_total_extremum_label / smallest_total_category_label / answer_and_annotation / sample 7899469009245855

- `instance_seed`: `7899469009245855`
- `word_count`: `77`
- `body_word_count`: `38`

```text
The figure shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Using the legend scale, compare the total values for all visible categories. What category label corresponds to the smallest scaled total?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the answer category row.
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[92,180,860,248],"answer":"Orchid"}
```

### task_charts__pictogram__category_total_extremum_label / smallest_total_category_label / answer_only / sample 7899469009245855

- `instance_seed`: `7899469009245855`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The figure shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Using the legend scale, compare the total values for all visible categories. What category label corresponds to the smallest scaled total?
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__pictogram__category_total_value / single / answer_and_annotation / sample 2108461655746099

- `instance_seed`: `2108461655746099`
- `word_count`: `63`
- `body_word_count`: `28`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Using the unit scale, what is the total for category "Olive"?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the requested category row.
Answer field: set "answer" to the requested integer value.
Example JSON:
{"annotation":[92,180,1160,248],"answer":42}
```

### task_charts__pictogram__category_total_value / single / answer_only / sample 2108461655746099

- `instance_seed`: `2108461655746099`
- `word_count`: `44`
- `body_word_count`: `28`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Using the unit scale, what is the total for category "Olive"?
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"answer":42}
```

### task_charts__pictogram__group_difference_value / single / answer_and_annotation / sample 4567004199418285

- `instance_seed`: `4567004199418285`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Compare "Sports" and "Hardware". What is the absolute difference in their totals?
Format for the "annotation" field: set "annotation" to an object mapping each compared category label to an [x0, y0, x1, y1] pixel box around that category row.
Format for the "answer" field: set "answer" to the requested integer value.
Example JSON:
{"annotation":{"M4":[92,270,1160,338],"Q8":[92,430,1160,498]},"answer":18}
```

### task_charts__pictogram__group_difference_value / single / answer_only / sample 4567004199418285

- `instance_seed`: `4567004199418285`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Compare "Sports" and "Hardware". What is the absolute difference in their totals?
Answer field: set "answer" to the requested integer value.
Example JSON:
{"answer":18}
```

### task_charts__pictogram__target_value_nearest_category_label / single / answer_and_annotation / sample 8584143864909842

- `instance_seed`: `8584143864909842`
- `word_count`: `66`
- `body_word_count`: `27`

```text
The image contains a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Which category's scaled total is nearest to 14?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the answer category row.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[92,180,860,248],"answer":"Orchid"}
```

### task_charts__pictogram__target_value_nearest_category_label / single / answer_only / sample 8584143864909842

- `instance_seed`: `8584143864909842`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The image contains a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Which category's scaled total is nearest to 14?
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__pictogram__threshold_count / greater_than_threshold / answer_and_annotation / sample 8046276650990811

- `instance_seed`: `8046276650990811`
- `word_count`: `94`
- `body_word_count`: `41`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Use the legend scale, then evaluate the requested threshold condition for each row. From the repeated marks, count categories with totals greater than 56.
Required annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel boxes around every category row with a total greater than the threshold.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[92,180,1160,248],[92,350,1160,418],[92,520,1160,588]],"answer":3}
```

### task_charts__pictogram__threshold_count / greater_than_threshold / answer_only / sample 8046276650990811

- `instance_seed`: `8046276650990811`
- `word_count`: `55`
- `body_word_count`: `41`

```text
The visual shows a repeated-mark pictogram where each icon represents the unit scale shown in the legend. Use the legend scale, then evaluate the requested threshold condition for each row. From the repeated marks, count categories with totals greater than 56.
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__pictogram__threshold_count / less_than_threshold / answer_and_annotation / sample 6557492322534187

- `instance_seed`: `6557492322534187`
- `word_count`: `93`
- `body_word_count`: `42`

```text
The figure shows a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Use the unit scale to compare each category total with the threshold. From the repeated marks, count categories with totals less than 30.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel boxes around every category row with a total less than the threshold.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[92,180,1160,248],[92,350,1160,418],[92,520,1160,588]],"answer":3}
```

### task_charts__pictogram__threshold_count / less_than_threshold / answer_only / sample 6557492322534187

- `instance_seed`: `6557492322534187`
- `word_count`: `56`
- `body_word_count`: `42`

```text
The figure shows a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend. Use the unit scale to compare each category total with the threshold. From the repeated marks, count categories with totals less than 30.
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / combined_total_at_least_threshold_count / answer_and_annotation / sample 6242098368101176

- `instance_seed`: `6242098368101176`
- `word_count`: `103`
- `body_word_count`: `51`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the two bar values in each row, how many age groups satisfy: the sum of "Urban" and "Rural" at least 150?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / combined_total_at_least_threshold_count / answer_only / sample 6242098368101176

- `instance_seed`: `6242098368101176`
- `word_count`: `67`
- `body_word_count`: `51`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the two bar values in each row, how many age groups satisfy: the sum of "Urban" and "Rural" at least 150?
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / combined_total_at_most_threshold_count / answer_and_annotation / sample 8226993020683672

- `instance_seed`: `8226993020683672`
- `word_count`: `94`
- `body_word_count`: `44`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the sum of "North" and "South" at most 120?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / combined_total_at_most_threshold_count / answer_only / sample 8226993020683672

- `instance_seed`: `8226993020683672`
- `word_count`: `58`
- `body_word_count`: `44`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the sum of "North" and "South" at most 120?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / left_side_at_least_threshold_count / answer_and_annotation / sample 4755439680293248

- `instance_seed`: `4755439680293248`
- `word_count`: `94`
- `body_word_count`: `42`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Group A" value at least 58?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / left_side_at_least_threshold_count / answer_only / sample 4755439680293248

- `instance_seed`: `4755439680293248`
- `word_count`: `56`
- `body_word_count`: `42`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Group A" value at least 58?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / left_side_at_most_threshold_count / answer_and_annotation / sample 2882397958298356

- `instance_seed`: `2882397958298356`
- `word_count`: `93`
- `body_word_count`: `41`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Baseline" value at most 63?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / left_side_at_most_threshold_count / answer_only / sample 2882397958298356

- `instance_seed`: `2882397958298356`
- `word_count`: `55`
- `body_word_count`: `41`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Baseline" value at most 63?
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / right_side_at_least_threshold_count / answer_and_annotation / sample 1372021348132430

- `instance_seed`: `1372021348132430`
- `word_count`: `97`
- `body_word_count`: `41`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Scenario" value at least 28?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / right_side_at_least_threshold_count / answer_only / sample 1372021348132430

- `instance_seed`: `1372021348132430`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many rows meet the condition the "Scenario" value at least 28?
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / right_side_at_most_threshold_count / answer_and_annotation / sample 6298440122984636

- `instance_seed`: `6298440122984636`
- `word_count`: `92`
- `body_word_count`: `40`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many age groups have the "Rural" value at most 48?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__age_group_threshold_count / right_side_at_most_threshold_count / answer_only / sample 6298440122984636

- `instance_seed`: `6298440122984636`
- `word_count`: `56`
- `body_word_count`: `40`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many age groups have the "Rural" value at most 48?
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__dominant_side_count / left_side_greater_count / answer_and_annotation / sample 3646372734571879

- `instance_seed`: `3646372734571879`
- `word_count`: `88`
- `body_word_count`: `38`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many age groups have "Baseline" greater than "Scenario"?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__dominant_side_count / left_side_greater_count / answer_only / sample 3646372734571879

- `instance_seed`: `3646372734571879`
- `word_count`: `52`
- `body_word_count`: `38`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. How many age groups have "Baseline" greater than "Scenario"?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__dominant_side_count / right_side_greater_count / answer_and_annotation / sample 4422312266247139

- `instance_seed`: `4422312266247139`
- `word_count`: `93`
- `body_word_count`: `41`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. For how many visible age groups does "Right cohort" exceed "Left cohort"?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around the two bars for each counted age-group row.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[278,214,1038,246],[278,338,1038,370],[278,524,1038,556]],"answer":3}
```

### task_charts__population_pyramid__dominant_side_count / right_side_greater_count / answer_only / sample 4422312266247139

- `instance_seed`: `4422312266247139`
- `word_count`: `54`
- `body_word_count`: `41`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. For how many visible age groups does "Right cohort" exceed "Left cohort"?
Answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__population_pyramid__side_gap_extremum_label / largest_side_gap_label / answer_and_annotation / sample 7029387803559925

- `instance_seed`: `7029387803559925`
- `word_count`: `90`
- `body_word_count`: `42`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the mirrored bar lengths, which age-group label has the largest left-right difference?
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the two bars in the answer row.
Format for the "answer" field: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[278,312,1038,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_gap_extremum_label / largest_side_gap_label / answer_only / sample 7029387803559925

- `instance_seed`: `7029387803559925`
- `word_count`: `60`
- `body_word_count`: `42`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the mirrored bar lengths, which age-group label has the largest left-right difference?
Final answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__population_pyramid__side_gap_extremum_label / smallest_nonzero_side_gap_label / answer_and_annotation / sample 3051724403164280

- `instance_seed`: `3051724403164280`
- `word_count`: `86`
- `body_word_count`: `43`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the mirrored bar lengths, which age-group label has the smallest nonzero left-right difference?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the two bars in the answer row.
Final answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[278,312,1038,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_gap_extremum_label / smallest_nonzero_side_gap_label / answer_only / sample 3051724403164280

- `instance_seed`: `3051724403164280`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using the mirrored bar lengths, which age-group label has the smallest nonzero left-right difference?
Answer field: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / left_side_largest_value_label / answer_and_annotation / sample 5374475997334550

- `instance_seed`: `5374475997334550`
- `word_count`: `77`
- `body_word_count`: `38`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Among the "Baseline" values, which age group is largest?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected side bar.
Answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[278,312,482,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / left_side_largest_value_label / answer_only / sample 5374475997334550

- `instance_seed`: `5374475997334550`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The chart shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Among the "Baseline" values, which age group is largest?
Required answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / left_side_smallest_value_label / answer_and_annotation / sample 8977528880482062

- `instance_seed`: `8977528880482062`
- `word_count`: `78`
- `body_word_count`: `37`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Find the age group where "Baseline" is smallest.
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected side bar.
Required answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[278,312,482,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / left_side_smallest_value_label / answer_only / sample 8977528880482062

- `instance_seed`: `8977528880482062`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The visual shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Find the age group where "Baseline" is smallest.
Answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / right_side_largest_value_label / answer_and_annotation / sample 3512206416030764

- `instance_seed`: `3512206416030764`
- `word_count`: `87`
- `body_word_count`: `42`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using only the "Right cohort" bars, which age-group label has the largest value?
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected side bar.
Format for the "answer" field: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[654,312,1038,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / right_side_largest_value_label / answer_only / sample 3512206416030764

- `instance_seed`: `3512206416030764`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The figure shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Using only the "Right cohort" bars, which age-group label has the largest value?
Answer field: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / right_side_smallest_value_label / answer_and_annotation / sample 7449313970440045

- `instance_seed`: `7449313970440045`
- `word_count`: `84`
- `body_word_count`: `39`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Among the "Right cohort" values, which age group is smallest?
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected side bar.
Format for the "answer" field: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"annotation":[654,312,1038,344],"answer":"40-44"}
```

### task_charts__population_pyramid__side_value_extremum_label / right_side_smallest_value_label / answer_only / sample 7449313970440045

- `instance_seed`: `7449313970440045`
- `word_count`: `57`
- `body_word_count`: `39`

```text
The image shows a mirrored horizontal bar chart with one row per age group. The left and right bars show the two legend series on the same positive scale. Among the "Right cohort" values, which age group is smallest?
Required answer format: set "answer" to the exact visible age-group label as a string.
Example JSON:
{"answer":"40-44"}
```

### task_charts__radar__highlighted_metric_threshold_panel_count / single / answer_and_annotation / sample 1501664949432541

- `instance_seed`: `1501664949432541`
- `word_count`: `98`
- `body_word_count`: `39`

```text
The visual shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. For the highlighted metric "Trossen", how many panels have values above threshold 6?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each radar panel whose highlighted metric is above the threshold.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[160,130,432,390],[516,130,788,390],[872,130,1144,390]],"answer":3}
```

### task_charts__radar__highlighted_metric_threshold_panel_count / single / answer_only / sample 1501664949432541

- `instance_seed`: `1501664949432541`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The visual shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. For the highlighted metric "Trossen", how many panels have values above threshold 6?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__radar__matching_condition_panel_count / single / answer_and_annotation / sample 6443795191103743

- `instance_seed`: `6443795191103743`
- `word_count`: `86`
- `body_word_count`: `39`

```text
The image shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. Across panels, how many radar charts have at least 4 spokes above 6?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each radar panel satisfying the condition.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[160,130,432,390],[516,130,788,390]],"answer":2}
```

### task_charts__radar__matching_condition_panel_count / single / answer_only / sample 6443795191103743

- `instance_seed`: `6443795191103743`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The image shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. Across panels, how many radar charts have at least 4 spokes above 6?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__radar__profile_advantage_count / single / answer_and_annotation / sample 8191111046558807

- `instance_seed`: `8191111046558807`
- `word_count`: `92`
- `body_word_count`: `36`

```text
The figure shows one radar chart with the same metric spokes for two colored profile polygons. The legend names the two profiles. What is the count of metrics where "Pueyo" has the larger value than "Szydlo"?
Required annotation format: set "annotation" to a list of segments. Each segment is [[x1, y1], [x2, y2]], using the two named profile points for one counted metric; use [] if no metrics match.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[650,244],[622,270]],[[744,430],[708,408]]],"answer":2}
```

### task_charts__radar__profile_advantage_count / single / answer_only / sample 8191111046558807

- `instance_seed`: `8191111046558807`
- `word_count`: `51`
- `body_word_count`: `36`

```text
The figure shows one radar chart with the same metric spokes for two colored profile polygons. The legend names the two profiles. What is the count of metrics where "Pueyo" has the larger value than "Szydlo"?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__radar__threshold_metric_count_for_panel / single / answer_and_annotation / sample 7240097281990054

- `instance_seed`: `7240097281990054`
- `word_count`: `78`
- `body_word_count`: `36`

```text
The image shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. In panel "FY26", how many metrics are above threshold 7?
Annotation format: set "annotation" to an array of [x,y] pixel points, one at each counted vertex in the queried panel.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[512,356],[588,420],[474,488]],"answer":3}
```

### task_charts__radar__threshold_metric_count_for_panel / single / answer_only / sample 7240097281990054

- `instance_seed`: `7240097281990054`
- `word_count`: `50`
- `body_word_count`: `36`

```text
The image shows small multiple radar charts. Each panel has the same metric spokes and one colored profile polygon; panel labels identify the separate radar charts. In panel "FY26", how many metrics are above threshold 7?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__radial_progress__extremum_remaining_label / highest_remaining_label / answer_and_annotation / sample 2960386704402453

- `instance_seed`: `2960386704402453`
- `word_count`: `76`
- `body_word_count`: `32`

```text
The image shows a grid of labeled segmented radial progress bars. Filled segments show completion from 0 to 100 percent. Among the displayed progress widgets, which label has the most remaining progress?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] pixel box around the answer widget.
Format for the "answer" field: set "answer" to the exact visible widget label as a string.
Example JSON:
{"annotation":[92,154,352,388],"answer":"Orchid"}
```

### task_charts__radial_progress__extremum_remaining_label / highest_remaining_label / answer_only / sample 2960386704402453

- `instance_seed`: `2960386704402453`
- `word_count`: `49`
- `body_word_count`: `45`

```text
The image shows a grid of labeled segmented radial progress bars. Filled segments show completion from 0 to 100 percent. Among the displayed progress widgets, which label has the most remaining progress?
Answer field: set "answer" to the exact visible widget label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__radial_progress__extremum_remaining_label / lowest_remaining_label / answer_and_annotation / sample 5068665938500917

- `instance_seed`: `5068665938500917`
- `word_count`: `72`
- `body_word_count`: `33`

```text
The visual shows a grid of labeled circular progress rings. Each ring shows completion from 0 to 100 percent. Find the progress widget with the least remaining progress. What is its visible label?
Final answer format: set "answer" to the exact visible widget label as a string.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the answer widget.
Example JSON:
{"annotation":[92,154,352,388],"answer":"Orchid"}
```

### task_charts__radial_progress__extremum_remaining_label / lowest_remaining_label / answer_only / sample 5068665938500917

- `instance_seed`: `5068665938500917`
- `word_count`: `53`
- `body_word_count`: `33`

```text
The visual shows a grid of labeled circular progress rings. Each ring shows completion from 0 to 100 percent. Find the progress widget with the least remaining progress. What is its visible label?
Format for the "answer" field: set "answer" to the exact visible widget label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__radial_progress__progress_interval_count / single / answer_and_annotation / sample 3567217259431981

- `instance_seed`: `3567217259431981`
- `word_count`: `78`
- `body_word_count`: `31`

```text
The image shows a grid of labeled circular progress rings. Each ring shows completion from 0 to 100 percent. Count the labeled progress widgets whose values are from 35% through 65%.
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each counted widget.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[92,154,352,388],[382,154,642,388],[672,154,932,388]],"answer":3}
```

### task_charts__radial_progress__progress_interval_count / single / answer_only / sample 3567217259431981

- `instance_seed`: `3567217259431981`
- `word_count`: `45`
- `body_word_count`: `31`

```text
The image shows a grid of labeled circular progress rings. Each ring shows completion from 0 to 100 percent. Count the labeled progress widgets whose values are from 35% through 65%.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__radial_progress__progress_threshold_count / at_least_threshold_count / answer_and_annotation / sample 2585449887415275

- `instance_seed`: `2585449887415275`
- `word_count`: `76`
- `body_word_count`: `31`

```text
The figure shows a grid of labeled semicircle progress gauges. Each gauge shows completion from 0 to 100 percent. Using the radial progress scale, how many widgets are at least 50%?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each counted widget.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[92,154,352,388],[382,154,642,388],[672,154,932,388]],"answer":3}
```

### task_charts__radial_progress__progress_threshold_count / at_least_threshold_count / answer_only / sample 2585449887415275

- `instance_seed`: `2585449887415275`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The figure shows a grid of labeled semicircle progress gauges. Each gauge shows completion from 0 to 100 percent. Using the radial progress scale, how many widgets are at least 50%?
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__radial_progress__progress_threshold_count / below_threshold_count / answer_and_annotation / sample 8599182896432177

- `instance_seed`: `8599182896432177`
- `word_count`: `74`
- `body_word_count`: `29`

```text
The visual shows a grid of labeled semicircle progress gauges. Each gauge shows completion from 0 to 100 percent. How many displayed progress indicators meet the condition below 60%?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes, one around each counted widget.
Answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[92,154,352,388],[382,154,642,388],[672,154,932,388]],"answer":3}
```

### task_charts__radial_progress__progress_threshold_count / below_threshold_count / answer_only / sample 8599182896432177

- `instance_seed`: `8599182896432177`
- `word_count`: `43`
- `body_word_count`: `29`

```text
The visual shows a grid of labeled semicircle progress gauges. Each gauge shows completion from 0 to 100 percent. How many displayed progress indicators meet the condition below 60%?
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__radial_sankey__dominant_endpoint_label / largest_source_for_target / answer_and_annotation / sample 8660450036430407

- `instance_seed`: `8660450036430407`
- `word_count`: `83`
- `body_word_count`: `38`

```text
The image shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. For target node "Mcewen", which source sends the largest flow?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected source node.
Format for the "answer" field: set "answer" to the exact visible source label as a string.
Example JSON:
{"annotation":[240,466,264,494],"answer":"B7P2"}
```

### task_charts__radial_sankey__dominant_endpoint_label / largest_source_for_target / answer_only / sample 8660450036430407

- `instance_seed`: `8660450036430407`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The image shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. For target node "Mcewen", which source sends the largest flow?
Answer field: set "answer" to the exact visible source label as a string.
Example JSON:
{"answer":"B7P2"}
```

### task_charts__radial_sankey__dominant_endpoint_label / largest_target_for_source / answer_and_annotation / sample 5722132468901726

- `instance_seed`: `5722132468901726`
- `word_count`: `80`
- `body_word_count`: `41`

```text
The visual shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. Among all curved bands leaving "GRAB", which target label has the highest value?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected target node.
Answer format: set "answer" to the exact visible target label as a string.
Example JSON:
{"annotation":[930,470,954,498],"answer":"Y4M8"}
```

### task_charts__radial_sankey__dominant_endpoint_label / largest_target_for_source / answer_only / sample 5722132468901726

- `instance_seed`: `5722132468901726`
- `word_count`: `61`
- `body_word_count`: `41`

```text
The visual shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. Among all curved bands leaving "GRAB", which target label has the highest value?
Format for the "answer" field: set "answer" to the exact visible target label as a string.
Example JSON:
{"answer":"Y4M8"}
```

### task_charts__radial_sankey__transfer_total_value / source_to_targets_total / answer_and_annotation / sample 1427359056081860

- `instance_seed`: `1427359056081860`
- `word_count`: `88`
- `body_word_count`: `41`

```text
The image shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. What total value is sent from "Rotich" to target nodes "Emigh" and "Fozard"?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the printed flow-value labels used in the calculation.
Required answer format: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[420,330,458,358],[560,394,598,422]],"answer":47}
```

### task_charts__radial_sankey__transfer_total_value / source_to_targets_total / answer_only / sample 1427359056081860

- `instance_seed`: `1427359056081860`
- `word_count`: `55`
- `body_word_count`: `41`

```text
The image shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. What total value is sent from "Rotich" to target nodes "Emigh" and "Fozard"?
Final answer format: set "answer" to the requested integer total.
Example JSON:
{"answer":47}
```

### task_charts__radial_sankey__transfer_total_value / sources_to_target_total / answer_and_annotation / sample 4018064473871469

- `instance_seed`: `4018064473871469`
- `word_count`: `87`
- `body_word_count`: `42`

```text
The visual shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. For target node "TMDX", what total flow comes from source nodes "AKCLY" and "MIRA"?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the printed flow-value labels used in the calculation.
Answer field: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[690,318,728,346],[612,430,650,458]],"answer":39}
```

### task_charts__radial_sankey__transfer_total_value / sources_to_target_total / answer_only / sample 4018064473871469

- `instance_seed`: `4018064473871469`
- `word_count`: `56`
- `body_word_count`: `42`

```text
The visual shows a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, and each curved band has a printed integer flow value. For target node "TMDX", what total flow comes from source nodes "AKCLY" and "MIRA"?
Required answer format: set "answer" to the requested integer total.
Example JSON:
{"answer":39}
```

### task_charts__region_map__adjacent_category_count / single / answer_and_annotation / sample 1005972857661635

- `instance_seed`: `1005972857661635`
- `word_count`: `85`
- `body_word_count`: `30`

```text
This image shows a synthetic map with colored regions, short region labels, and a legend. From the map legend, count edge-or-corner neighboring colored regions touching region "Q92" in category "Books".
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the counted neighboring regions.
Format for the "answer" field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[132,182,218,250],[252,178,338,246],[398,266,484,334]],"answer":3}
```

### task_charts__region_map__adjacent_category_count / single / answer_only / sample 1005972857661635

- `instance_seed`: `1005972857661635`
- `word_count`: `47`
- `body_word_count`: `30`

```text
This image shows a synthetic map with colored regions, short region labels, and a legend. From the map legend, count edge-or-corner neighboring colored regions touching region "Q92" in category "Books".
Answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__adjacent_numeric_threshold_count / greater_than_adjacent_numeric_threshold_count / answer_and_annotation / sample 5681022928317654

- `instance_seed`: `5681022928317654`
- `word_count`: `81`
- `body_word_count`: `34`

```text
The image shows a synthetic map with colored regions, short region labels, and a legend. What number of colored regions touching region "Z48" by edge or corner fall in value bins greater than 59?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the counted neighboring regions.
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[132,182,218,250],[252,178,338,246]],"answer":2}
```

### task_charts__region_map__adjacent_numeric_threshold_count / greater_than_adjacent_numeric_threshold_count / answer_only / sample 5681022928317654

- `instance_seed`: `5681022928317654`
- `word_count`: `52`
- `body_word_count`: `34`

```text
The image shows a synthetic map with colored regions, short region labels, and a legend. What number of colored regions touching region "Z48" by edge or corner fall in value bins greater than 59?
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":2}
```

### task_charts__region_map__adjacent_numeric_threshold_count / less_than_adjacent_numeric_threshold_count / answer_and_annotation / sample 2023591415678889

- `instance_seed`: `2023591415678889`
- `word_count`: `78`
- `body_word_count`: `31`

```text
The map shows a synthetic map with colored regions, short region labels, and a legend. Count the colored regions touching region "N33" by edge or corner with values less than 20.
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the counted neighboring regions.
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[132,182,218,250],[252,178,338,246]],"answer":2}
```

### task_charts__region_map__adjacent_numeric_threshold_count / less_than_adjacent_numeric_threshold_count / answer_only / sample 2023591415678889

- `instance_seed`: `2023591415678889`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The map shows a synthetic map with colored regions, short region labels, and a legend. Count the colored regions touching region "N33" by edge or corner with values less than 20.
Answer field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":2}
```

### task_charts__region_map__adjacent_same_category_count / single / answer_and_annotation / sample 2989664826639657

- `instance_seed`: `2989664826639657`
- `word_count`: `79`
- `body_word_count`: `28`

```text
This image shows a synthetic map with colored regions, short region labels, and a legend. Using the category legend, how many edge-or-corner neighboring colored regions match region "D6"?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes for the counted neighboring regions.
Format for the "answer" field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[132,182,218,250],[252,178,338,246]],"answer":2}
```

### task_charts__region_map__adjacent_same_category_count / single / answer_only / sample 2989664826639657

- `instance_seed`: `2989664826639657`
- `word_count`: `46`
- `body_word_count`: `28`

```text
This image shows a synthetic map with colored regions, short region labels, and a legend. Using the category legend, how many edge-or-corner neighboring colored regions match region "D6"?
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":2}
```

### task_charts__region_map__categorical_region_count / single / answer_and_annotation / sample 6392565210033488

- `instance_seed`: `6392565210033488`
- `word_count`: `63`
- `body_word_count`: `18`

```text
This image shows a synthetic map with colored regions and a legend. Count the regions assigned to "Medium".
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the counted regions.
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[175,216],[295,212],[441,300]],"answer":3}
```

### task_charts__region_map__categorical_region_count / single / answer_only / sample 6392565210033488

- `instance_seed`: `6392565210033488`
- `word_count`: `35`
- `body_word_count`: `18`

```text
This image shows a synthetic map with colored regions and a legend. Count the regions assigned to "Medium".
Answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__group_category_region_count / single / answer_and_annotation / sample 5915259938059355

- `instance_seed`: `5915259938059355`
- `word_count`: `83`
- `body_word_count`: `34`

```text
This image shows a world map with selected countries colored by category and a category legend. Using the world map and category legend, how many visible colored countries in "South America" fall under "River"?
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points at the centers of the counted regions.
Format for the "answer" field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[175,216],[295,212],[441,300]],"answer":3}
```

### task_charts__region_map__group_category_region_count / single / answer_only / sample 5915259938059355

- `instance_seed`: `5915259938059355`
- `word_count`: `52`
- `body_word_count`: `34`

```text
This image shows a world map with selected countries colored by category and a category legend. Using the world map and category legend, how many visible colored countries in "South America" fall under "River"?
Final answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__marker_region_extremum_label / largest_marker_region_extremum_label / answer_and_annotation / sample 578552305808650

- `instance_seed`: `578552305808650`
- `word_count`: `68`
- `body_word_count`: `24`

```text
This image shows a United States map with marker bubbles over selected states. From the marker layer, which visible label has the largest value?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point at the center of the answer marker bubble.
Format for the "answer" field: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[441,251],"answer":"D"}
```

### task_charts__region_map__marker_region_extremum_label / largest_marker_region_extremum_label / answer_only / sample 578552305808650

- `instance_seed`: `578552305808650`
- `word_count`: `42`
- `body_word_count`: `24`

```text
This image shows a United States map with marker bubbles over selected states. From the marker layer, which visible label has the largest value?
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"D"}
```

### task_charts__region_map__marker_region_extremum_label / smallest_marker_region_extremum_label / answer_and_annotation / sample 3467471443927069

- `instance_seed`: `3467471443927069`
- `word_count`: `63`
- `body_word_count`: `23`

```text
This image shows a synthetic map with marker bubbles over selected regions. From the marker layer, which visible label has the smallest value?
Required annotation format: set "annotation" to one [x,y] pixel point at the center of the answer marker bubble.
Required answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"annotation":[441,251],"answer":"D"}
```

### task_charts__region_map__marker_region_extremum_label / smallest_marker_region_extremum_label / answer_only / sample 3467471443927069

- `instance_seed`: `3467471443927069`
- `word_count`: `40`
- `body_word_count`: `23`

```text
This image shows a synthetic map with marker bubbles over selected regions. From the marker layer, which visible label has the smallest value?
Answer format: set "answer" to the exact visible region label as a string.
Example JSON:
{"answer":"D"}
```

### task_charts__region_map__marker_region_threshold_count / greater_than_marker_region_threshold_count / answer_and_annotation / sample 1821137416283903

- `instance_seed`: `1821137416283903`
- `word_count`: `69`
- `body_word_count`: `23`

```text
The map shows a synthetic map with marker bubbles over selected regions. Count the regions whose marker bubbles encode values greater than 1.
Annotation format: set "annotation" to an array of [x,y] pixel points, one at the center of each counted marker bubble.
Final answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[193,233],[333,273],[473,223]],"answer":3}
```

### task_charts__region_map__marker_region_threshold_count / greater_than_marker_region_threshold_count / answer_only / sample 1821137416283903

- `instance_seed`: `1821137416283903`
- `word_count`: `41`
- `body_word_count`: `23`

```text
The map shows a synthetic map with marker bubbles over selected regions. Count the regions whose marker bubbles encode values greater than 1.
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__marker_region_threshold_count / less_than_marker_region_threshold_count / answer_and_annotation / sample 7896887687874452

- `instance_seed`: `7896887687874452`
- `word_count`: `72`
- `body_word_count`: `25`

```text
The visual shows a European Union map with marker bubbles over selected countries. Using the marker bubbles, how many countries have values less than 4?
Required annotation format: set "annotation" to an array of [x,y] pixel points, one at the center of each counted marker bubble.
Required answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[193,233],[333,273],[473,223]],"answer":3}
```

### task_charts__region_map__marker_region_threshold_count / less_than_marker_region_threshold_count / answer_only / sample 7896887687874452

- `instance_seed`: `7896887687874452`
- `word_count`: `42`
- `body_word_count`: `25`

```text
The visual shows a European Union map with marker bubbles over selected countries. Using the marker bubbles, how many countries have values less than 4?
Answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__named_region_set_total_value / single / answer_and_annotation / sample 8429831198556853

- `instance_seed`: `8429831198556853`
- `word_count`: `88`
- `body_word_count`: `33`

```text
The visual shows a map with colored regions, visible region labels, visible integer values, and a legend. Using the visible region labels, what is the combined value for "Audit set": "P", "R", "F"?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the regions included in the total.
Format for the "answer" field: set "answer" to the requested total as an integer.
Example JSON:
{"annotation":[[132,182,218,250],[252,178,338,246],[398,266,484,334]],"answer":126}
```

### task_charts__region_map__named_region_set_total_value / single / answer_only / sample 8429831198556853

- `instance_seed`: `8429831198556853`
- `word_count`: `51`
- `body_word_count`: `33`

```text
The visual shows a map with colored regions, visible region labels, visible integer values, and a legend. Using the visible region labels, what is the combined value for "Audit set": "P", "R", "F"?
Format for the "answer" field: set "answer" to the requested total as an integer.
Example JSON:
{"answer":126}
```

### task_charts__region_map__numeric_interval_region_count / single / answer_and_annotation / sample 2619882096664684

- `instance_seed`: `2619882096664684`
- `word_count`: `76`
- `body_word_count`: `31`

```text
The visual shows an EU country map with selected countries colored by value and a color legend. From the map legend, count countries whose values are between 33 and 65, inclusive.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the counted regions.
Answer field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[193,247],[303,255],[417,259],[529,267]],"answer":4}
```

### task_charts__region_map__numeric_interval_region_count / single / answer_only / sample 2619882096664684

- `instance_seed`: `2619882096664684`
- `word_count`: `48`
- `body_word_count`: `31`

```text
The visual shows an EU country map with selected countries colored by value and a color legend. From the map legend, count countries whose values are between 33 and 65, inclusive.
Answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":4}
```

### task_charts__region_map__numeric_threshold_region_count / greater_than_numeric_threshold_region_count / answer_and_annotation / sample 1620238631251227

- `instance_seed`: `1620238631251227`
- `word_count`: `64`
- `body_word_count`: `20`

```text
The figure shows a synthetic map with colored regions and a legend. Count the regions with values greater than 74.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the counted regions.
Final answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[185,225],[385,223],[487,307]],"answer":3}
```

### task_charts__region_map__numeric_threshold_region_count / greater_than_numeric_threshold_region_count / answer_only / sample 1620238631251227

- `instance_seed`: `1620238631251227`
- `word_count`: `38`
- `body_word_count`: `20`

```text
The figure shows a synthetic map with colored regions and a legend. Count the regions with values greater than 74.
Final answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__region_map__numeric_threshold_region_count / less_than_numeric_threshold_region_count / answer_and_annotation / sample 4101703626194784

- `instance_seed`: `4101703626194784`
- `word_count`: `78`
- `body_word_count`: `29`

```text
This image shows an EU country map with selected countries colored by value and a color legend. From the map legend, count countries whose values are less than 50.
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points at the centers of the counted regions.
Format for the "answer" field: set "answer" to the requested number of regions as an integer.
Example JSON:
{"annotation":[[185,225],[385,223],[487,307]],"answer":3}
```

### task_charts__region_map__numeric_threshold_region_count / less_than_numeric_threshold_region_count / answer_only / sample 4101703626194784

- `instance_seed`: `4101703626194784`
- `word_count`: `46`
- `body_word_count`: `29`

```text
This image shows an EU country map with selected countries colored by value and a color legend. From the map legend, count countries whose values are less than 50.
Answer format: set "answer" to the requested number of regions as an integer.
Example JSON:
{"answer":3}
```

### task_charts__sankey__node_side_total_value / source_outgoing_total_flow / answer_and_annotation / sample 8537430204921201

- `instance_seed`: `8537430204921201`
- `word_count`: `85`
- `body_word_count`: `46`

```text
This image shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. For source node "Taran", sum every outgoing band value.
Annotation format: set "annotation" to an array of [x,y] pixel points at every printed outgoing flow-value label used in the sum.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[390,197],[384,309]],"answer":31}
```

### task_charts__sankey__node_side_total_value / source_outgoing_total_flow / answer_only / sample 8537430204921201

- `instance_seed`: `8537430204921201`
- `word_count`: `61`
- `body_word_count`: `46`

```text
This image shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. For source node "Taran", sum every outgoing band value.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"answer":31}
```

### task_charts__sankey__node_side_total_value / target_incoming_total_flow / answer_and_annotation / sample 2514184689319104

- `instance_seed`: `2514184689319104`
- `word_count`: `88`
- `body_word_count`: `49`

```text
The visual shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. What is the sum of all printed values on bands entering "Earlen"?
Annotation format: set "annotation" to an array of [x,y] pixel points at every printed incoming flow-value label used in the sum.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[800,203],[800,299]],"answer":34}
```

### task_charts__sankey__node_side_total_value / target_incoming_total_flow / answer_only / sample 2514184689319104

- `instance_seed`: `2514184689319104`
- `word_count`: `61`
- `body_word_count`: `57`

```text
The visual shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. What is the sum of all printed values on bands entering "Earlen"?
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":34}
```

### task_charts__sankey__path_bottleneck_value / single / answer_and_annotation / sample 1484064254620493

- `instance_seed`: `1484064254620493`
- `word_count`: `89`
- `body_word_count`: `49`

```text
The image shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. On the two-band path "FXB" -> "EQT" -> "MALG", what is the bottleneck integer?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point at the printed value label for the bottleneck band.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"annotation":[390,235],"answer":12}
```

### task_charts__sankey__path_bottleneck_value / single / answer_only / sample 1484064254620493

- `instance_seed`: `1484064254620493`
- `word_count`: `62`
- `body_word_count`: `49`

```text
The image shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. On the two-band path "FXB" -> "EQT" -> "MALG", what is the bottleneck integer?
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":12}
```

### task_charts__sankey__source_to_target_total_flow / single / answer_and_annotation / sample 1684253097859187

- `instance_seed`: `1684253097859187`
- `word_count`: `96`
- `body_word_count`: `56`

```text
The figure shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. What is the total usable flow from "PRTH" to "EOI" if each two-band route contributes its smaller printed value?
Annotation format: set "annotation" to an array of [x,y] pixel points at all selected route bottleneck value labels used in the sum.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[390,197],[800,299]],"answer":27}
```

### task_charts__sankey__source_to_target_total_flow / single / answer_only / sample 1684253097859187

- `instance_seed`: `1684253097859187`
- `word_count`: `71`
- `body_word_count`: `56`

```text
The figure shows a three-column Sankey-style flow diagram. Each node has a visible label, each directed band has a printed integer value, and bands run from a source node through one middle node to a target node. What is the total usable flow from "PRTH" to "EOI" if each two-band route contributes its smaller printed value?
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"answer":27}
```

### task_charts__scatter_cluster__centroid_option_selection_label / single / answer_and_annotation / sample 2419115372802407

- `instance_seed`: `2419115372802407`
- `word_count`: `67`
- `body_word_count`: `27`

```text
The figure shows a scatter plot with several colored point clusters and a matching legend. Which option marker best matches the center of mass of cluster "Sendai"?
Required annotation format: set "annotation" to the [x,y] pixel point at the center of the selected option marker.
Final answer format: set "answer" to the selected option letter as a capital letter.
Example JSON:
{"annotation":[327,291],"answer":"D"}
```

### task_charts__scatter_cluster__centroid_option_selection_label / single / answer_only / sample 2419115372802407

- `instance_seed`: `2419115372802407`
- `word_count`: `45`
- `body_word_count`: `27`

```text
The figure shows a scatter plot with several colored point clusters and a matching legend. Which option marker best matches the center of mass of cluster "Sendai"?
Required answer format: set "answer" to the selected option letter as a capital letter.
Example JSON:
{"answer":"D"}
```

### task_charts__scatter_cluster__cluster_area_rank_label / largest_cluster_area_label / answer_and_annotation / sample 6913309614812645

- `instance_seed`: `6913309614812645`
- `word_count`: `65`
- `body_word_count`: `26`

```text
This image shows a scatter plot with several colored point clusters, shaded cluster footprints, and a matching legend. Which cluster's shaded footprint has the largest area?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster's shaded footprint.
Answer field: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[145,255,276,344],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_area_rank_label / largest_cluster_area_label / answer_only / sample 6913309614812645

- `instance_seed`: `6913309614812645`
- `word_count`: `42`
- `body_word_count`: `26`

```text
This image shows a scatter plot with several colored point clusters, shaded cluster footprints, and a matching legend. Which cluster's shaded footprint has the largest area?
Answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_area_rank_label / smallest_cluster_area_label / answer_and_annotation / sample 257269096079594

- `instance_seed`: `257269096079594`
- `word_count`: `69`
- `body_word_count`: `28`

```text
This image shows a scatter plot with several colored point clusters, shaded cluster footprints, and a matching legend. Which labeled cluster has the smallest shaded footprint by area?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster's shaded footprint.
Final answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[145,255,276,344],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_area_rank_label / smallest_cluster_area_label / answer_only / sample 257269096079594

- `instance_seed`: `257269096079594`
- `word_count`: `47`
- `body_word_count`: `28`

```text
This image shows a scatter plot with several colored point clusters, shaded cluster footprints, and a matching legend. Which labeled cluster has the smallest shaded footprint by area?
Format for the "answer" field: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_horizontal_spread_label / answer_and_annotation / sample 3277032329260783

- `instance_seed`: `3277032329260783`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. What cluster label has the largest spread in the horizontal direction?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Answer field: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_horizontal_spread_label / answer_only / sample 3277032329260783

- `instance_seed`: `3277032329260783`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. What cluster label has the largest spread in the horizontal direction?
Answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_overall_spread_label / answer_and_annotation / sample 1987371820626792

- `instance_seed`: `1987371820626792`
- `word_count`: `66`
- `body_word_count`: `26`

```text
The image shows a scatter plot with several colored point clusters and a matching legend. Compare the point-cloud shapes. Which cluster has the largest overall spread?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Required answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_overall_spread_label / answer_only / sample 1987371820626792

- `instance_seed`: `1987371820626792`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The image shows a scatter plot with several colored point clusters and a matching legend. Compare the point-cloud shapes. Which cluster has the largest overall spread?
Final answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_vertical_spread_label / answer_and_annotation / sample 6955162206932422

- `instance_seed`: `6955162206932422`
- `word_count`: `62`
- `body_word_count`: `22`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the largest vertical spread?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Final answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / largest_vertical_spread_label / answer_only / sample 6955162206932422

- `instance_seed`: `6955162206932422`
- `word_count`: `41`
- `body_word_count`: `22`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the largest vertical spread?
Format for the "answer" field: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_horizontal_spread_label / answer_and_annotation / sample 1348946905912839

- `instance_seed`: `1348946905912839`
- `word_count`: `64`
- `body_word_count`: `24`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. Which cluster has points with the smallest horizontal spread?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Required answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_horizontal_spread_label / answer_only / sample 1348946905912839

- `instance_seed`: `1348946905912839`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The visual shows a scatter plot with several colored point clusters and a matching legend. Which cluster has points with the smallest horizontal spread?
Answer field: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_overall_spread_label / answer_and_annotation / sample 1598613397165527

- `instance_seed`: `1598613397165527`
- `word_count`: `62`
- `body_word_count`: `22`

```text
This image shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the smallest overall spread?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Final answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_overall_spread_label / answer_only / sample 1598613397165527

- `instance_seed`: `1598613397165527`
- `word_count`: `39`
- `body_word_count`: `22`

```text
This image shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the smallest overall spread?
Required answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_vertical_spread_label / answer_and_annotation / sample 2160856777841304

- `instance_seed`: `2160856777841304`
- `word_count`: `62`
- `body_word_count`: `24`

```text
The figure shows a scatter plot with several colored point clusters and a matching legend. Find the labeled cluster with the smallest vertical dispersion.
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Answer field: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_spread_extremum_label / smallest_vertical_spread_label / answer_only / sample 2160856777841304

- `instance_seed`: `2160856777841304`
- `word_count`: `40`
- `body_word_count`: `24`

```text
The figure shows a scatter plot with several colored point clusters and a matching legend. Find the labeled cluster with the smallest vertical dispersion.
Answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_trend_direction_label / downward_trend_label / answer_and_annotation / sample 7113560787875326

- `instance_seed`: `7113560787875326`
- `word_count`: `66`
- `body_word_count`: `22`

```text
The chart shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the strongest downward trend?
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Format for the "answer" field: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_trend_direction_label / downward_trend_label / answer_only / sample 7113560787875326

- `instance_seed`: `7113560787875326`
- `word_count`: `41`
- `body_word_count`: `22`

```text
The chart shows a scatter plot with several colored point clusters and a matching legend. Which cluster has the strongest downward trend?
Format for the "answer" field: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_trend_direction_label / upward_trend_label / answer_and_annotation / sample 1896576659910192

- `instance_seed`: `1896576659910192`
- `word_count`: `66`
- `body_word_count`: `26`

```text
The chart shows a scatter plot with several colored point clusters and a matching legend. Find the labeled cluster whose points show the strongest upward trend.
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer cluster hull.
Final answer format: set "answer" to the requested cluster label as a string.
Example JSON:
{"annotation":[220,360,340,455],"answer":"Cobalt"}
```

### task_charts__scatter_cluster__cluster_trend_direction_label / upward_trend_label / answer_only / sample 1896576659910192

- `instance_seed`: `1896576659910192`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The chart shows a scatter plot with several colored point clusters and a matching legend. Find the labeled cluster whose points show the strongest upward trend.
Answer field: set "answer" to the requested cluster label as a string.
Example JSON:
{"answer":"Cobalt"}
```

### task_charts__scatter_points__axis_threshold_point_count / x_above_threshold_count / answer_and_annotation / sample 4845521540172947

- `instance_seed`: `4845521540172947`
- `word_count`: `66`
- `body_word_count`: `25`

```text
The chart shows a scatter plot of individual data points with numeric x- and y-axes. Count the points whose x-axis values are greater than 80.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / x_above_threshold_count / answer_only / sample 4845521540172947

- `instance_seed`: `4845521540172947`
- `word_count`: `41`
- `body_word_count`: `25`

```text
The chart shows a scatter plot of individual data points with numeric x- and y-axes. Count the points whose x-axis values are greater than 80.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / x_below_threshold_count / answer_and_annotation / sample 19037395780012

- `instance_seed`: `19037395780012`
- `word_count`: `66`
- `body_word_count`: `24`

```text
The image shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy x less than 70?
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / x_below_threshold_count / answer_only / sample 19037395780012

- `instance_seed`: `19037395780012`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The image shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy x less than 70?
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / y_above_threshold_count / answer_and_annotation / sample 2915148277924664

- `instance_seed`: `2915148277924664`
- `word_count`: `65`
- `body_word_count`: `24`

```text
The visual shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy y greater than 70?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / y_above_threshold_count / answer_only / sample 2915148277924664

- `instance_seed`: `2915148277924664`
- `word_count`: `42`
- `body_word_count`: `24`

```text
The visual shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy y greater than 70?
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / y_below_threshold_count / answer_and_annotation / sample 5343075299485487

- `instance_seed`: `5343075299485487`
- `word_count`: `65`
- `body_word_count`: `24`

```text
The visual shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy y less than 20?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__axis_threshold_point_count / y_below_threshold_count / answer_only / sample 5343075299485487

- `instance_seed`: `5343075299485487`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The visual shows a scatter plot of individual data points with numeric x- and y-axes. How many plotted points satisfy y less than 20?
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / largest_mean_x_category_label / answer_and_annotation / sample 2763911608578769

- `instance_seed`: `2763911608578769`
- `word_count`: `72`
- `body_word_count`: `32`

```text
The image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Using all points in each category, what category has the largest mean x-axis value?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer category's point cluster.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[210,260,675,438],"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / largest_mean_x_category_label / answer_only / sample 2763911608578769

- `instance_seed`: `2763911608578769`
- `word_count`: `50`
- `body_word_count`: `32`

```text
The image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Using all points in each category, what category has the largest mean x-axis value?
Required answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / largest_mean_y_category_label / answer_and_annotation / sample 6489535576427573

- `instance_seed`: `6489535576427573`
- `word_count`: `66`
- `body_word_count`: `26`

```text
The chart shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Which category has the largest mean y-axis value?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer category's point cluster.
Answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[210,260,675,438],"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / largest_mean_y_category_label / answer_only / sample 6489535576427573

- `instance_seed`: `6489535576427573`
- `word_count`: `46`
- `body_word_count`: `26`

```text
The chart shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Which category has the largest mean y-axis value?
Format for the "answer" field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / smallest_mean_x_category_label / answer_and_annotation / sample 440397185234210

- `instance_seed`: `440397185234210`
- `word_count`: `73`
- `body_word_count`: `31`

```text
The visual shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Compare the category point clouds. Which category has the smallest average x-axis position?
Required annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer category's point cluster.
Required answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[210,260,675,438],"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / smallest_mean_x_category_label / answer_only / sample 440397185234210

- `instance_seed`: `440397185234210`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The visual shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Compare the category point clouds. Which category has the smallest average x-axis position?
Final answer format: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / smallest_mean_y_category_label / answer_and_annotation / sample 3438217901136750

- `instance_seed`: `3438217901136750`
- `word_count`: `75`
- `body_word_count`: `29`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Find the category with the smallest average value along the y-axis.
Format for the "annotation" field: set "annotation" to the [x0,y0,x1,y1] pixel box around the answer category's point cluster.
Format for the "answer" field: set "answer" to the exact visible category label as a string.
Example JSON:
{"annotation":[210,260,675,438],"answer":"Orchid"}
```

### task_charts__scatter_points__category_axis_mean_extremum_label / smallest_mean_y_category_label / answer_only / sample 3438217901136750

- `instance_seed`: `3438217901136750`
- `word_count`: `46`
- `body_word_count`: `42`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Find the category with the smallest average value along the y-axis.
Answer field: set "answer" to the exact visible category label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scatter_points__category_threshold_point_count / category_x_above_threshold_count / answer_and_annotation / sample 8775353123982780

- `instance_seed`: `8775353123982780`
- `word_count`: `75`
- `body_word_count`: `35`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. For the visible category "Software", what is the number of points with x-axis values greater than 50?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_x_above_threshold_count / answer_only / sample 8775353123982780

- `instance_seed`: `8775353123982780`
- `word_count`: `53`
- `body_word_count`: `35`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. For the visible category "Software", what is the number of points with x-axis values greater than 50?
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_x_below_threshold_count / answer_and_annotation / sample 1076015868268316

- `instance_seed`: `1076015868268316`
- `word_count`: `75`
- `body_word_count`: `35`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. For the visible category "Pending", what is the number of points with x-axis values less than 70?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Answer field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_x_below_threshold_count / answer_only / sample 1076015868268316

- `instance_seed`: `1076015868268316`
- `word_count`: `53`
- `body_word_count`: `35`

```text
This image shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. For the visible category "Pending", what is the number of points with x-axis values less than 70?
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_y_above_threshold_count / answer_and_annotation / sample 6805333948227123

- `instance_seed`: `6805333948227123`
- `word_count`: `71`
- `body_word_count`: `31`

```text
The visual shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Within category "Closed", count the points whose y-axis values are greater than 60.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_y_above_threshold_count / answer_only / sample 6805333948227123

- `instance_seed`: `6805333948227123`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The visual shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. Within category "Closed", count the points whose y-axis values are greater than 60.
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_y_below_threshold_count / answer_and_annotation / sample 3461457301658064

- `instance_seed`: `3461457301658064`
- `word_count`: `71`
- `body_word_count`: `30`

```text
The figure shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. How many plotted points from category "Complete" satisfy y less than 60?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the supporting data points.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[230,410],[512,288]],"answer":2}
```

### task_charts__scatter_points__category_threshold_point_count / category_y_below_threshold_count / answer_only / sample 3461457301658064

- `instance_seed`: `3461457301658064`
- `word_count`: `45`
- `body_word_count`: `30`

```text
The figure shows a categorized scatter plot with individual data points, numeric x- and y-axes, and a legend. How many plotted points from category "Complete" satisfy y less than 60?
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__scatter_readout__series_pair_value_gap_at_x / single / answer_and_annotation / sample 2956683141314070

- `instance_seed`: `2956683141314070`
- `word_count`: `70`
- `body_word_count`: `29`

```text
This image shows a multi-series scatter plot with labeled points and a legend. Read both series "27Q4" and "27Q2" at x-axis label "T11". What is their absolute y-value gap?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] connecting the centers of the two compared scatter marks.
Answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"annotation":[[420,250],[420,310]],"answer":24}
```

### task_charts__scatter_readout__series_pair_value_gap_at_x / single / answer_only / sample 2956683141314070

- `instance_seed`: `2956683141314070`
- `word_count`: `46`
- `body_word_count`: `29`

```text
This image shows a multi-series scatter plot with labeled points and a legend. Read both series "27Q4" and "27Q2" at x-axis label "T11". What is their absolute y-value gap?
Required answer format: set "answer" to the requested absolute difference as an integer.
Example JSON:
{"answer":24}
```

### task_charts__scatter_readout__series_value_at_x_value / single / answer_and_annotation / sample 7989298725158025

- `instance_seed`: `7989298725158025`
- `word_count`: `62`
- `body_word_count`: `25`

```text
The image shows a multi-series scatter plot with labeled points and a legend. For series "FY29" at x-axis label "Sep", what y-axis value is shown?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected scatter mark.
Answer format: set "answer" to the requested y-axis value as an integer.
Example JSON:
{"annotation":[420,250],"answer":63}
```

### task_charts__scatter_readout__series_value_at_x_value / single / answer_only / sample 7989298725158025

- `instance_seed`: `7989298725158025`
- `word_count`: `44`
- `body_word_count`: `25`

```text
The image shows a multi-series scatter plot with labeled points and a legend. For series "FY29" at x-axis label "Sep", what y-axis value is shown?
Format for the "answer" field: set "answer" to the requested y-axis value as an integer.
Example JSON:
{"answer":63}
```

### task_charts__scatter_readout__series_x_extremum_label / series_highest_x_label / answer_and_annotation / sample 2621846827104593

- `instance_seed`: `2621846827104593`
- `word_count`: `88`
- `body_word_count`: `42`

```text
The visual shows a multi-series scatter plot with labeled points and a legend. Find the point where series "Earth" has its highest y-axis value. What is the x-axis label? If the requested series is not visible in the legend, answer exactly "unanswerable".
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected scatter mark; if the answer is "unanswerable", use an empty object.
Answer field: set "answer" to the requested x-axis label as a string.
Example JSON:
{"annotation":[420,250],"answer":"2016"}
```

### task_charts__scatter_readout__series_x_extremum_label / series_highest_x_label / answer_only / sample 2621846827104593

- `instance_seed`: `2621846827104593`
- `word_count`: `59`
- `body_word_count`: `42`

```text
The visual shows a multi-series scatter plot with labeled points and a legend. Find the point where series "Earth" has its highest y-axis value. What is the x-axis label? If the requested series is not visible in the legend, answer exactly "unanswerable".
Required answer format: set "answer" to the requested x-axis label as a string.
Example JSON:
{"answer":"2016"}
```

### task_charts__scatter_readout__series_x_extremum_label / series_lowest_x_label / answer_and_annotation / sample 7019208725499476

- `instance_seed`: `7019208725499476`
- `word_count`: `86`
- `body_word_count`: `66`

```text
The image shows a multi-series scatter plot with labeled points and a legend. For series "Yemen", what x-axis label corresponds to its lowest y-axis value? If the requested series is not visible in the legend, answer exactly "unanswerable".
Final annotation format: set "annotation" to one [x,y] pixel point at the center of the selected scatter mark; if the answer is "unanswerable", use an empty object.
Final answer format: set "answer" to the requested x-axis label as a string.
Example JSON:
{"annotation":[420,250],"answer":"2016"}
```

### task_charts__scatter_readout__series_x_extremum_label / series_lowest_x_label / answer_only / sample 7019208725499476

- `instance_seed`: `7019208725499476`
- `word_count`: `54`
- `body_word_count`: `38`

```text
The image shows a multi-series scatter plot with labeled points and a legend. For series "Yemen", what x-axis label corresponds to its lowest y-axis value? If the requested series is not visible in the legend, answer exactly "unanswerable".
Answer format: set "answer" to the requested x-axis label as a string.
Example JSON:
{"answer":"2016"}
```

### task_charts__scatter_readout__series_y_anchor_other_series_value / single / answer_and_annotation / sample 4876845197623

- `instance_seed`: `4876845197623`
- `word_count`: `79`
- `body_word_count`: `32`

```text
The visual shows a multi-series scatter plot with labeled points and a legend. Series "22Q1" includes a point labeled 14. At the same x-axis position, what value is printed for series "22Q2"?
Format for the "annotation" field: set "annotation" to one [x,y] pixel point at the center of the comparison-series scatter mark that gives the answer.
Format for the "answer" field: set "answer" to the requested y-axis value as an integer.
Example JSON:
{"annotation":[520,310],"answer":63}
```

### task_charts__scatter_readout__series_y_anchor_other_series_value / single / answer_only / sample 4876845197623

- `instance_seed`: `4876845197623`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The visual shows a multi-series scatter plot with labeled points and a legend. Series "22Q1" includes a point labeled 14. At the same x-axis position, what value is printed for series "22Q2"?
Required answer format: set "answer" to the requested y-axis value as an integer.
Example JSON:
{"answer":63}
```

### task_charts__scatter_readout__x_value_rank_series_label / x_highest_series_label / answer_and_annotation / sample 8500088901913768

- `instance_seed`: `8500088901913768`
- `word_count`: `65`
- `body_word_count`: `26`

```text
The chart shows a multi-series scatter plot with labeled points and a legend. Compare all series at "Sep". Which visible series has the highest y-axis value?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the answer series scatter mark.
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[520,310],"answer":"Orchid"}
```

### task_charts__scatter_readout__x_value_rank_series_label / x_highest_series_label / answer_only / sample 8500088901913768

- `instance_seed`: `8500088901913768`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The chart shows a multi-series scatter plot with labeled points and a legend. Compare all series at "Sep". Which visible series has the highest y-axis value?
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scatter_readout__x_value_rank_series_label / x_lowest_series_label / answer_and_annotation / sample 2460098160604224

- `instance_seed`: `2460098160604224`
- `word_count`: `65`
- `body_word_count`: `24`

```text
The figure shows a multi-series scatter plot with labeled points and a legend. At x-axis label "Sep", which series has the lowest y-axis value?
Required annotation format: set "annotation" to one [x,y] pixel point at the center of the answer series scatter mark.
Required answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[520,310],"answer":"Orchid"}
```

### task_charts__scatter_readout__x_value_rank_series_label / x_lowest_series_label / answer_only / sample 2460098160604224

- `instance_seed`: `2460098160604224`
- `word_count`: `41`
- `body_word_count`: `24`

```text
The figure shows a multi-series scatter plot with labeled points and a legend. At x-axis label "Sep", which series has the lowest y-axis value?
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"Orchid"}
```

### task_charts__scientific_axis_frame__axis_span_value / x_axis_span_value / answer_and_annotation / sample 6068237502043366

- `instance_seed`: `6068237502043366`
- `word_count`: `74`
- `body_word_count`: `27`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. What range width is shown by the visible tick labels on the x-axis?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the smallest visible tick mark to the largest visible tick mark on the requested axis.
Answer format: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[108,612],[1018,612]],"answer":48}
```

### task_charts__scientific_axis_frame__axis_span_value / x_axis_span_value / answer_only / sample 6068237502043366

- `instance_seed`: `6068237502043366`
- `word_count`: `43`
- `body_word_count`: `27`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. What range width is shown by the visible tick labels on the x-axis?
Final answer format: set "answer" to the requested value as an integer.
Example JSON:
{"answer":48}
```

### task_charts__scientific_axis_frame__axis_span_value / y_axis_span_value / answer_and_annotation / sample 1054411050364081

- `instance_seed`: `1054411050364081`
- `word_count`: `75`
- `body_word_count`: `28`

```text
The image shows a scientific plot frame with numeric x-axis and y-axis tick labels. Find the difference between the largest and smallest visible tick labels on the y-axis.
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the smallest visible tick mark to the largest visible tick mark on the requested axis.
Answer field: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[108,612],[108,90]],"answer":48}
```

### task_charts__scientific_axis_frame__axis_span_value / y_axis_span_value / answer_only / sample 1054411050364081

- `instance_seed`: `1054411050364081`
- `word_count`: `44`
- `body_word_count`: `28`

```text
The image shows a scientific plot frame with numeric x-axis and y-axis tick labels. Find the difference between the largest and smallest visible tick labels on the y-axis.
Final answer format: set "answer" to the requested value as an integer.
Example JSON:
{"answer":48}
```

### task_charts__scientific_axis_frame__tick_spacing_value / x_first_tick_spacing_value / answer_and_annotation / sample 2741515872022686

- `instance_seed`: `2741515872022686`
- `word_count`: `78`
- `body_word_count`: `29`

```text
The image shows a scientific plot frame with numeric x-axis and y-axis tick labels. What is the difference between the first and second visible tick labels on the x-axis?
Required annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the first visible tick mark to the second visible tick mark on the requested axis.
Required answer format: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[210,612],[358,612]],"answer":10}
```

### task_charts__scientific_axis_frame__tick_spacing_value / x_first_tick_spacing_value / answer_only / sample 2741515872022686

- `instance_seed`: `2741515872022686`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The image shows a scientific plot frame with numeric x-axis and y-axis tick labels. What is the difference between the first and second visible tick labels on the x-axis?
Answer field: set "answer" to the requested value as an integer.
Example JSON:
{"answer":10}
```

### task_charts__scientific_axis_frame__tick_spacing_value / x_last_tick_spacing_value / answer_and_annotation / sample 2397768892098434

- `instance_seed`: `2397768892098434`
- `word_count`: `78`
- `body_word_count`: `29`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. On the x-axis, what is the numeric spacing between the last two visible tick labels?
Required annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the second-to-last visible tick mark to the last visible tick mark on the requested axis.
Required answer format: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[640,612],[812,612]],"answer":12}
```

### task_charts__scientific_axis_frame__tick_spacing_value / x_last_tick_spacing_value / answer_only / sample 2397768892098434

- `instance_seed`: `2397768892098434`
- `word_count`: `44`
- `body_word_count`: `29`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. On the x-axis, what is the numeric spacing between the last two visible tick labels?
Answer format: set "answer" to the requested value as an integer.
Example JSON:
{"answer":12}
```

### task_charts__scientific_axis_frame__tick_spacing_value / y_first_tick_spacing_value / answer_and_annotation / sample 4146615433482426

- `instance_seed`: `4146615433482426`
- `word_count`: `77`
- `body_word_count`: `29`

```text
The visual shows a scientific plot frame with numeric x-axis and y-axis tick labels. For the first pair of neighboring tick labels on the y-axis, what is the interval?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the first visible tick mark to the second visible tick mark on the requested axis.
Final answer format: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[108,612],[108,500]],"answer":10}
```

### task_charts__scientific_axis_frame__tick_spacing_value / y_first_tick_spacing_value / answer_only / sample 4146615433482426

- `instance_seed`: `4146615433482426`
- `word_count`: `44`
- `body_word_count`: `29`

```text
The visual shows a scientific plot frame with numeric x-axis and y-axis tick labels. For the first pair of neighboring tick labels on the y-axis, what is the interval?
Answer format: set "answer" to the requested value as an integer.
Example JSON:
{"answer":10}
```

### task_charts__scientific_axis_frame__tick_spacing_value / y_last_tick_spacing_value / answer_and_annotation / sample 4990752942613445

- `instance_seed`: `4990752942613445`
- `word_count`: `77`
- `body_word_count`: `29`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. For the final pair of neighboring tick labels on the y-axis, what is the interval?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the second-to-last visible tick mark to the last visible tick mark on the requested axis.
Final answer format: set "answer" to the requested value as an integer.
Example JSON:
{"annotation":[[108,238],[108,126]],"answer":12}
```

### task_charts__scientific_axis_frame__tick_spacing_value / y_last_tick_spacing_value / answer_only / sample 4990752942613445

- `instance_seed`: `4990752942613445`
- `word_count`: `44`
- `body_word_count`: `29`

```text
The chart shows a scientific plot frame with numeric x-axis and y-axis tick labels. For the final pair of neighboring tick labels on the y-axis, what is the interval?
Answer format: set "answer" to the requested value as an integer.
Example JSON:
{"answer":12}
```

### task_charts__single_series__endpoint_change_value / absolute_endpoint_change_value / answer_and_annotation / sample 7858672157083817

- `instance_seed`: `7858672157083817`
- `word_count`: `76`
- `body_word_count`: `31`

```text
The image shows an ordered labeled horizontal bar chart where each bar length is read from the horizontal axis from top to bottom. Compute |value at "Q6X3" minus value at "V8Z7"|.
Final answer format: set "answer" to the requested endpoint-change value as an integer.
Annotation format: set "annotation" to an object mapping "start_mark" and "end_mark" to [x,y] pixel points on the two endpoint marks.
Example JSON:
{"annotation":{"start_mark":[160,420],"end_mark":[460,220]},"answer":20}
```

### task_charts__single_series__endpoint_change_value / absolute_endpoint_change_value / answer_only / sample 7858672157083817

- `instance_seed`: `7858672157083817`
- `word_count`: `47`
- `body_word_count`: `31`

```text
The image shows an ordered labeled horizontal bar chart where each bar length is read from the horizontal axis from top to bottom. Compute |value at "Q6X3" minus value at "V8Z7"|.
Answer format: set "answer" to the requested endpoint-change value as an integer.
Example JSON:
{"answer":20}
```

### task_charts__single_series__endpoint_change_value / percent_endpoint_change_value / answer_and_annotation / sample 1944391247120151

- `instance_seed`: `1944391247120151`
- `word_count`: `104`
- `body_word_count`: `43`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Compute the signed percent change from "Sim" to "Act"; use the integer percentage without a percent sign, negative if it decreased.
Format for the "annotation" field: set "annotation" to an object mapping "start_mark" and "end_mark" to [x,y] pixel points on the two endpoint marks.
Format for the "answer" field: set "answer" to the requested signed integer percentage change, omitting the percent sign and using a negative value for a decrease.
Example JSON:
{"annotation":{"start_mark":[160,420],"end_mark":[460,220]},"answer":20}
```

### task_charts__single_series__endpoint_change_value / percent_endpoint_change_value / answer_only / sample 1944391247120151

- `instance_seed`: `1944391247120151`
- `word_count`: `71`
- `body_word_count`: `43`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Compute the signed percent change from "Sim" to "Act"; use the integer percentage without a percent sign, negative if it decreased.
Final answer format: set "answer" to the requested signed integer percentage change, omitting the percent sign and using a negative value for a decrease.
Example JSON:
{"answer":20}
```

### task_charts__single_series__endpoint_change_value / signed_endpoint_change_value / answer_and_annotation / sample 6044485875351245

- `instance_seed`: `6044485875351245`
- `word_count`: `80`
- `body_word_count`: `34`

```text
The image shows an ordered labeled lollipop chart where point labels identify y-values from left to right. How much did the value change from "Siwa" to "Witu", using a negative answer for a decrease?
Required annotation format: set "annotation" to an object mapping "start_mark" and "end_mark" to [x,y] pixel points on the two endpoint marks.
Required answer format: set "answer" to the requested endpoint-change value as an integer.
Example JSON:
{"annotation":{"start_mark":[160,420],"end_mark":[460,220]},"answer":20}
```

### task_charts__single_series__endpoint_change_value / signed_endpoint_change_value / answer_only / sample 6044485875351245

- `instance_seed`: `6044485875351245`
- `word_count`: `51`
- `body_word_count`: `34`

```text
The image shows an ordered labeled lollipop chart where point labels identify y-values from left to right. How much did the value change from "Siwa" to "Witu", using a negative answer for a decrease?
Final answer format: set "answer" to the requested endpoint-change value as an integer.
Example JSON:
{"answer":20}
```

### task_charts__single_series__interval_rate_value / single / answer_and_annotation / sample 7170440994101281

- `instance_seed`: `7170440994101281`
- `word_count`: `75`
- `body_word_count`: `29`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find the nonnegative integer average rate of change from "P3K7" to "F3W6".
Annotation format: set "annotation" to an object mapping "start_mark" and "end_mark" to [x,y] pixel points on the two endpoint marks.
Answer field: set "answer" to the requested nonnegative absolute average rate as an integer.
Example JSON:
{"annotation":{"start_mark":[200,420],"end_mark":[500,240]},"answer":6}
```

### task_charts__single_series__interval_rate_value / single / answer_only / sample 7170440994101281

- `instance_seed`: `7170440994101281`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find the nonnegative integer average rate of change from "P3K7" to "F3W6".
Answer format: set "answer" to the requested nonnegative absolute average rate as an integer.
Example JSON:
{"answer":6}
```

### task_charts__single_series__interval_value_count / single / answer_and_annotation / sample 2164165896295237

- `instance_seed`: `2164165896295237`
- `word_count`: `75`
- `body_word_count`: `29`

```text
The image shows an ordered labeled lollipop chart where point labels identify y-values from left to right. What number of labeled marks lie in the inclusive interval [1, 14]?
Required annotation format: set "annotation" to an array of [x,y] pixel points on every mark whose value is inside the inclusive interval.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[165,310],[380,250],[590,285]],"answer":3}
```

### task_charts__single_series__interval_value_count / single / answer_only / sample 2164165896295237

- `instance_seed`: `2164165896295237`
- `word_count`: `45`
- `body_word_count`: `29`

```text
The image shows an ordered labeled lollipop chart where point labels identify y-values from left to right. What number of labeled marks lie in the inclusive interval [1, 14]?
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__single_series__monotone_streak_length / longest_decreasing_streak_length / answer_and_annotation / sample 5855152490206466

- `instance_seed`: `5855152490206466`
- `word_count`: `82`
- `body_word_count`: `35`

```text
The image shows an ordered labeled area chart where point labels identify y-values from left to right. Determine the length of the longest streak where each consecutive label decreases in value. Count labels, not gaps.
Annotation format: set "annotation" to an array of [x,y] pixel points on every mark in the unique longest matching monotone streak.
Answer field: set "answer" to the requested streak length as an integer.
Example JSON:
{"annotation":[[180,420],[300,350],[420,260],[540,170]],"answer":4}
```

### task_charts__single_series__monotone_streak_length / longest_decreasing_streak_length / answer_only / sample 5855152490206466

- `instance_seed`: `5855152490206466`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The image shows an ordered labeled area chart where point labels identify y-values from left to right. Determine the length of the longest streak where each consecutive label decreases in value. Count labels, not gaps.
Required answer format: set "answer" to the requested streak length as an integer.
Example JSON:
{"answer":4}
```

### task_charts__single_series__monotone_streak_length / longest_increasing_streak_length / answer_and_annotation / sample 3814564677672747

- `instance_seed`: `3814564677672747`
- `word_count`: `82`
- `body_word_count`: `35`

```text
The image shows an ordered labeled horizontal bar chart where each bar length is read from the horizontal axis from top to bottom. Compute the length of the longest strictly increasing run of consecutive labels.
Annotation format: set "annotation" to an array of [x,y] pixel points on every mark in the unique longest matching monotone streak.
Answer field: set "answer" to the requested streak length as an integer.
Example JSON:
{"annotation":[[180,420],[300,350],[420,260],[540,170]],"answer":4}
```

### task_charts__single_series__monotone_streak_length / longest_increasing_streak_length / answer_only / sample 3814564677672747

- `instance_seed`: `3814564677672747`
- `word_count`: `51`
- `body_word_count`: `35`

```text
The image shows an ordered labeled horizontal bar chart where each bar length is read from the horizontal axis from top to bottom. Compute the length of the longest strictly increasing run of consecutive labels.
Answer format: set "answer" to the requested streak length as an integer.
Example JSON:
{"answer":4}
```

### task_charts__single_series__observed_threshold_crossing_label / observed_above_threshold_crossing_label / answer_and_annotation / sample 4196362682639225

- `instance_seed`: `4196362682639225`
- `word_count`: `63`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Starting from the first label, which label first exceeds 44?
Required annotation format: set "annotation" to one [x,y] pixel point on the first threshold-crossing mark.
Required answer format: set "answer" to the requested crossing label as a string.
Example JSON:
{"annotation":[360,240],"answer":"C4A7"}
```

### task_charts__single_series__observed_threshold_crossing_label / observed_above_threshold_crossing_label / answer_only / sample 4196362682639225

- `instance_seed`: `4196362682639225`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Starting from the first label, which label first exceeds 44?
Required answer format: set "answer" to the requested crossing label as a string.
Example JSON:
{"answer":"C4A7"}
```

### task_charts__single_series__observed_threshold_crossing_label / observed_below_threshold_crossing_label / answer_and_annotation / sample 2942406015611141

- `instance_seed`: `2942406015611141`
- `word_count`: `71`
- `body_word_count`: `35`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. What is the first label where the chart value crosses below threshold 28?
Required annotation format: set "annotation" to one [x,y] pixel point on the first threshold-crossing mark.
Required answer format: set "answer" to the requested crossing label as a string.
Example JSON:
{"annotation":[360,240],"answer":"C4A7"}
```

### task_charts__single_series__observed_threshold_crossing_label / observed_below_threshold_crossing_label / answer_only / sample 2942406015611141

- `instance_seed`: `2942406015611141`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. What is the first label where the chart value crosses below threshold 28?
Answer field: set "answer" to the requested crossing label as a string.
Example JSON:
{"answer":"C4A7"}
```

### task_charts__single_series__order_statistic_label / median_order_statistic_label / answer_and_annotation / sample 8032631223320689

- `instance_seed`: `8032631223320689`
- `word_count`: `65`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find the label of the mark with the median value.
Annotation format: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Answer field: set "answer" to the exact visible label of the selected mark as a string.
Example JSON:
{"annotation":[420,180],"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_label / median_order_statistic_label / answer_only / sample 8032631223320689

- `instance_seed`: `8032631223320689`
- `word_count`: `48`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find the label of the mark with the median value.
Final answer format: set "answer" to the exact visible label of the selected mark as a string.
Example JSON:
{"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_label / nth_highest_order_statistic_label / answer_and_annotation / sample 84520177359906

- `instance_seed`: `84520177359906`
- `word_count`: `73`
- `body_word_count`: `29`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Find the label of the mark with the 3rd-highest distinct displayed value.
Format for the "annotation" field: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Format for the "answer" field: set "answer" to the exact visible label of the selected mark as a string.
Example JSON:
{"annotation":[420,180],"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_label / nth_highest_order_statistic_label / answer_only / sample 84520177359906

- `instance_seed`: `84520177359906`
- `word_count`: `50`
- `body_word_count`: `29`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Find the label of the mark with the 3rd-highest distinct displayed value.
Final answer format: set "answer" to the exact visible label of the selected mark as a string.
Example JSON:
{"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_label / nth_lowest_order_statistic_label / answer_and_annotation / sample 1558652484076916

- `instance_seed`: `1558652484076916`
- `word_count`: `73`
- `body_word_count`: `34`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Find the label of the mark with the 3rd-lowest distinct displayed value.
Final answer format: set "answer" to the exact visible label of the selected mark as a string.
Annotation format: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Example JSON:
{"annotation":[420,180],"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_label / nth_lowest_order_statistic_label / answer_only / sample 1558652484076916

- `instance_seed`: `1558652484076916`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Find the label of the mark with the 3rd-lowest distinct displayed value.
Answer field: set "answer" to the exact visible label of the selected mark as a string.
Example JSON:
{"answer":"K7P2"}
```

### task_charts__single_series__order_statistic_value / median_order_statistic_value / answer_and_annotation / sample 1543639025569650

- `instance_seed`: `1543639025569650`
- `word_count`: `64`
- `body_word_count`: `30`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Find the median value among the labeled marks.
Final answer format: set "answer" to the requested statistic as an integer.
Annotation format: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Example JSON:
{"annotation":[300,240],"answer":6}
```

### task_charts__single_series__order_statistic_value / median_order_statistic_value / answer_only / sample 1543639025569650

- `instance_seed`: `1543639025569650`
- `word_count`: `46`
- `body_word_count`: `30`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. Find the median value among the labeled marks.
Required answer format: set "answer" to the requested statistic as an integer.
Example JSON:
{"answer":6}
```

### task_charts__single_series__order_statistic_value / nth_highest_order_statistic_value / answer_and_annotation / sample 370815446277620

- `instance_seed`: `370815446277620`
- `word_count`: `60`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Compute the 3rd-highest distinct displayed value for the displayed values.
Annotation format: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Answer field: set "answer" to the requested statistic as an integer.
Example JSON:
{"annotation":[300,240],"answer":6}
```

### task_charts__single_series__order_statistic_value / nth_highest_order_statistic_value / answer_only / sample 370815446277620

- `instance_seed`: `370815446277620`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Compute the 3rd-highest distinct displayed value for the displayed values.
Answer field: set "answer" to the requested statistic as an integer.
Example JSON:
{"answer":6}
```

### task_charts__single_series__order_statistic_value / nth_lowest_order_statistic_value / answer_and_annotation / sample 3584791424376595

- `instance_seed`: `3584791424376595`
- `word_count`: `60`
- `body_word_count`: `27`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Find the 3rd-lowest distinct displayed value among the labeled marks.
Annotation format: set "annotation" to one [x,y] pixel point on the selected statistic mark.
Answer field: set "answer" to the requested statistic as an integer.
Example JSON:
{"annotation":[300,240],"answer":6}
```

### task_charts__single_series__order_statistic_value / nth_lowest_order_statistic_value / answer_only / sample 3584791424376595

- `instance_seed`: `3584791424376595`
- `word_count`: `43`
- `body_word_count`: `27`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Find the 3rd-lowest distinct displayed value among the labeled marks.
Final answer format: set "answer" to the requested statistic as an integer.
Example JSON:
{"answer":6}
```

### task_charts__single_series__remaining_mean_after_removal / single / answer_and_annotation / sample 4350287515964998

- `instance_seed`: `4350287515964998`
- `word_count`: `92`
- `body_word_count`: `33`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. If labels "Colt" and "Rad" were removed, what would be the mean of the remaining labels?
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on the chart marks whose values remain in the average after the stated removals.
Format for the "answer" field: set "answer" to the requested integer value; for percentage questions, omit the percent sign.
Example JSON:
{"annotation":[[180,360],[320,240],[460,300]],"answer":18}
```

### task_charts__single_series__remaining_mean_after_removal / single / answer_only / sample 4350287515964998

- `instance_seed`: `4350287515964998`
- `word_count`: `56`
- `body_word_count`: `33`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. If labels "Colt" and "Rad" were removed, what would be the mean of the remaining labels?
Format for the "answer" field: set "answer" to the requested integer value; for percentage questions, omit the percent sign.
Example JSON:
{"answer":18}
```

### task_charts__single_series__target_share_after_removal / single / answer_and_annotation / sample 3563566696098001

- `instance_seed`: `3563566696098001`
- `word_count`: `87`
- `body_word_count`: `33`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Remove labels "Ba" and "Tori". What integer percent of the remaining sum comes from label "Pene"?
Final answer format: set "answer" to the requested integer value; for percentage questions, omit the percent sign.
Annotation format: set "annotation" to an array of [x,y] pixel points on the chart marks whose values remain in the total after the stated removals.
Example JSON:
{"annotation":[[180,260],[320,340],[460,220]],"answer":25}
```

### task_charts__single_series__target_share_after_removal / single / answer_only / sample 3563566696098001

- `instance_seed`: `3563566696098001`
- `word_count`: `53`
- `body_word_count`: `49`

```text
The image shows an ordered labeled dot plot where point labels identify y-values from left to right. Remove labels "Ba" and "Tori". What integer percent of the remaining sum comes from label "Pene"?
Answer field: set "answer" to the requested integer value; for percentage questions, omit the percent sign.
Example JSON:
{"answer":25}
```

### task_charts__single_series__threshold_value_count / above_threshold_count / answer_and_annotation / sample 8730972896475712

- `instance_seed`: `8730972896475712`
- `word_count`: `72`
- `body_word_count`: `26`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find how many labeled marks are greater than 18.
Final answer format: set "answer" to the requested count as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points on every mark whose value is strictly greater than the threshold.
Example JSON:
{"annotation":[[180,260],[390,180],[610,320]],"answer":3}
```

### task_charts__single_series__threshold_value_count / above_threshold_count / answer_only / sample 8730972896475712

- `instance_seed`: `8730972896475712`
- `word_count`: `41`
- `body_word_count`: `26`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Find how many labeled marks are greater than 18.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__single_series__threshold_value_count / below_threshold_count / answer_and_annotation / sample 7072686486713127

- `instance_seed`: `7072686486713127`
- `word_count`: `74`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Determine how many marks show values strictly less than 15.
Required annotation format: set "annotation" to an array of [x,y] pixel points on every mark whose value is strictly less than the threshold.
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[160,420],[280,360],[520,390]],"answer":3}
```

### task_charts__single_series__threshold_value_count / below_threshold_count / answer_only / sample 7072686486713127

- `instance_seed`: `7072686486713127`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The image shows an ordered labeled line chart where point labels identify y-values from left to right. Determine how many marks show values strictly less than 15.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__single_series__turning_point_count / peak_turning_point_count / answer_and_annotation / sample 4241346670552517

- `instance_seed`: `4241346670552517`
- `word_count`: `92`
- `body_word_count`: `45`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. How many local peaks are present? A local peak has a value higher than the immediately previous and next labels in displayed order.
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points on all local turning points of the requested type.
Format for the "answer" field: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[220,180],[520,210]],"answer":2}
```

### task_charts__single_series__turning_point_count / peak_turning_point_count / answer_only / sample 4241346670552517

- `instance_seed`: `4241346670552517`
- `word_count`: `60`
- `body_word_count`: `45`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. How many local peaks are present? A local peak has a value higher than the immediately previous and next labels in displayed order.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__single_series__turning_point_count / trough_turning_point_count / answer_and_annotation / sample 2922716681624957

- `instance_seed`: `2922716681624957`
- `word_count`: `87`
- `body_word_count`: `45`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. How many local troughs are present? A local trough has a value lower than the immediately previous and next labels in displayed order.
Final answer format: set "answer" to the requested count as an integer.
Annotation format: set "annotation" to an array of [x,y] pixel points on all local turning points of the requested type.
Example JSON:
{"annotation":[[220,180],[520,210]],"answer":2}
```

### task_charts__single_series__turning_point_count / trough_turning_point_count / answer_only / sample 2922716681624957

- `instance_seed`: `2922716681624957`
- `word_count`: `61`
- `body_word_count`: `45`

```text
The image shows an ordered labeled bar chart where each bar height is read from the vertical axis from left to right. How many local troughs are present? A local trough has a value lower than the immediately previous and next labels in displayed order.
Final answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__size_encoding__category_relative_size_count / larger_than_reference_in_category_count / answer_and_annotation / sample 2216301247197343

- `instance_seed`: `2216301247197343`
- `word_count`: `104`
- `body_word_count`: `33`

```text
The image shows a rectangular word cloud where item text size indicates value and a colored marker beside each word indicates category. For category "Maple", how many labels are size-encoded larger than "FY29"?
Annotation format: set "annotation" to an object mapping "reference_item" to an array containing one [x0, y0, x1, y1] box for the reference item and "counted_items" to an array of [x0, y0, x1, y1] boxes for the counted items.
Final answer format: set "answer" to the requested number of items as an integer.
Example JSON:
{"annotation":{"reference_item":[[238,460,322,544]],"counted_items":[[628,306,710,388],[720,250,780,310]]},"answer":2}
```

### task_charts__size_encoding__category_relative_size_count / larger_than_reference_in_category_count / answer_only / sample 2216301247197343

- `instance_seed`: `2216301247197343`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The image shows a rectangular word cloud where item text size indicates value and a colored marker beside each word indicates category. For category "Maple", how many labels are size-encoded larger than "FY29"?
Answer field: set "answer" to the requested number of items as an integer.
Example JSON:
{"answer":2}
```

### task_charts__size_encoding__category_relative_size_count / smaller_than_reference_in_category_count / answer_and_annotation / sample 7831717971214557

- `instance_seed`: `7831717971214557`
- `word_count`: `103`
- `body_word_count`: `33`

```text
The image shows a circular word cloud where item text size indicates value and a colored marker beside each word indicates category. Within category "Azure", how many items are smaller than item "Vaunda"?
Annotation format: set "annotation" to an object mapping "reference_item" to an array containing one [x0, y0, x1, y1] box for the reference item and "counted_items" to an array of [x0, y0, x1, y1] boxes for the counted items.
Answer field: set "answer" to the requested number of items as an integer.
Example JSON:
{"annotation":{"reference_item":[[238,460,322,544]],"counted_items":[[628,306,710,388],[720,250,780,310]]},"answer":2}
```

### task_charts__size_encoding__category_relative_size_count / smaller_than_reference_in_category_count / answer_only / sample 7831717971214557

- `instance_seed`: `7831717971214557`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The image shows a circular word cloud where item text size indicates value and a colored marker beside each word indicates category. Within category "Azure", how many items are smaller than item "Vaunda"?
Answer format: set "answer" to the requested number of items as an integer.
Example JSON:
{"answer":2}
```

### task_charts__size_encoding__filtered_item_extremum_label / largest_size_item_in_category_label / answer_and_annotation / sample 2484510574955615

- `instance_seed`: `2484510574955615`
- `word_count`: `74`
- `body_word_count`: `33`

```text
The image shows a circular word cloud where item text size indicates value and a colored marker beside each word indicates category. Among the "Azure" items, which label corresponds to the largest item?
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Answer field: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__filtered_item_extremum_label / largest_size_item_in_category_label / answer_only / sample 2484510574955615

- `instance_seed`: `2484510574955615`
- `word_count`: `53`
- `body_word_count`: `33`

```text
The image shows a circular word cloud where item text size indicates value and a colored marker beside each word indicates category. Among the "Azure" items, which label corresponds to the largest item?
Answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__size_encoding__filtered_item_extremum_label / smallest_size_item_in_category_label / answer_and_annotation / sample 8486613402539155

- `instance_seed`: `8486613402539155`
- `word_count`: `68`
- `body_word_count`: `27`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Among the "Health" items, which label corresponds to the smallest item?
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__filtered_item_extremum_label / smallest_size_item_in_category_label / answer_only / sample 8486613402539155

- `instance_seed`: `8486613402539155`
- `word_count`: `48`
- `body_word_count`: `27`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Among the "Health" items, which label corresponds to the smallest item?
Final answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__size_encoding__global_item_extremum_category_label / largest_overall_size_category_label / answer_and_annotation / sample 4827781037788109

- `instance_seed`: `4827781037788109`
- `word_count`: `71`
- `body_word_count`: `30`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Find the single item with the largest size. What category does it belong to?
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Answer field: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__global_item_extremum_category_label / largest_overall_size_category_label / answer_only / sample 4827781037788109

- `instance_seed`: `4827781037788109`
- `word_count`: `53`
- `body_word_count`: `30`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Find the single item with the largest size. What category does it belong to?
Format for the "answer" field: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__size_encoding__global_item_extremum_category_label / smallest_overall_size_category_label / answer_and_annotation / sample 6462829993978389

- `instance_seed`: `6462829993978389`
- `word_count`: `65`
- `body_word_count`: `24`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Which category contains the globally smallest size-encoded item?
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__global_item_extremum_category_label / smallest_overall_size_category_label / answer_only / sample 6462829993978389

- `instance_seed`: `6462829993978389`
- `word_count`: `45`
- `body_word_count`: `24`

```text
The image shows a packed bubble chart where bubble size indicates value and color indicates category. Which category contains the globally smallest size-encoded item?
Required answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__size_encoding__panel_category_extremum_panel_label / largest_category_item_panel_label / answer_and_annotation / sample 7266522202310953

- `instance_seed`: `7266522202310953`
- `word_count`: `70`
- `body_word_count`: `28`

```text
The image shows multiple packed bubble-chart panels where bubble size indicates value and color indicates category. For category "Sierra", which panel contains the item with the largest size?
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Final answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__panel_category_extremum_panel_label / largest_category_item_panel_label / answer_only / sample 7266522202310953

- `instance_seed`: `7266522202310953`
- `word_count`: `49`
- `body_word_count`: `28`

```text
The image shows multiple packed bubble-chart panels where bubble size indicates value and color indicates category. For category "Sierra", which panel contains the item with the largest size?
Required answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__size_encoding__panel_category_extremum_panel_label / smallest_category_item_panel_label / answer_and_annotation / sample 1245763665496411

- `instance_seed`: `1245763665496411`
- `word_count`: `76`
- `body_word_count`: `29`

```text
The image shows multiple packed bubble-chart panels where bubble size indicates value and color indicates category. Looking only at category "Music", name the panel that contains the smallest item.
Format for the "annotation" field: set "annotation" to one bounding box [x0, y0, x1, y1] around the answer item.
Format for the "answer" field: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"annotation":[410,235,548,292],"answer":"Aero"}
```

### task_charts__size_encoding__panel_category_extremum_panel_label / smallest_category_item_panel_label / answer_only / sample 1245763665496411

- `instance_seed`: `1245763665496411`
- `word_count`: `50`
- `body_word_count`: `29`

```text
The image shows multiple packed bubble-chart panels where bubble size indicates value and color indicates category. Looking only at category "Music", name the panel that contains the smallest item.
Final answer format: set "answer" to the exact visible item, category, or panel label as a string.
Example JSON:
{"answer":"Aero"}
```

### task_charts__style_legend__series_extremum_x_label / series_highest_x_label / answer_and_annotation / sample 4921324468920540

- `instance_seed`: `4921324468920540`
- `word_count`: `80`
- `body_word_count`: `38`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Trace series "Tyishia" across the plot. Which visible x label marks its maximum value?
Annotation format: set "annotation" to a single [x,y] pixel point at the center of the plotted point used to answer.
Final answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[510,230],"answer":"Q3"}
```

### task_charts__style_legend__series_extremum_x_label / series_highest_x_label / answer_only / sample 4921324468920540

- `instance_seed`: `4921324468920540`
- `word_count`: `55`
- `body_word_count`: `38`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Trace series "Tyishia" across the plot. Which visible x label marks its maximum value?
Answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"Q3"}
```

### task_charts__style_legend__series_extremum_x_label / series_lowest_x_label / answer_and_annotation / sample 7829050037640465

- `instance_seed`: `7829050037640465`
- `word_count`: `78`
- `body_word_count`: `36`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Which x-axis label corresponds to the smallest plotted value for series "SZZL"?
Annotation format: set "annotation" to a single [x,y] pixel point at the center of the plotted point used to answer.
Final answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[510,230],"answer":"Q3"}
```

### task_charts__style_legend__series_extremum_x_label / series_lowest_x_label / answer_only / sample 7829050037640465

- `instance_seed`: `7829050037640465`
- `word_count`: `54`
- `body_word_count`: `36`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Which x-axis label corresponds to the smallest plotted value for series "SZZL"?
Final answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"Q3"}
```

### task_charts__style_legend__threshold_series_count / above_threshold_series_count / answer_and_annotation / sample 365125991813603

- `instance_seed`: `365125991813603`
- `word_count`: `79`
- `body_word_count`: `35`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Using the legend styles, count the series above 40 at "Gueppi".
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the plotted points used to answer.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[610,210],[610,285],[610,360]],"answer":3}
```

### task_charts__style_legend__threshold_series_count / above_threshold_series_count / answer_only / sample 365125991813603

- `instance_seed`: `365125991813603`
- `word_count`: `51`
- `body_word_count`: `35`

```text
The chart shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Using the legend styles, count the series above 40 at "Gueppi".
Required answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__style_legend__threshold_series_count / below_threshold_series_count / answer_and_annotation / sample 3324060879820023

- `instance_seed`: `3324060879820023`
- `word_count`: `82`
- `body_word_count`: `38`

```text
The plotted figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. At "Land", how many visible series markers are below the threshold value 60?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the plotted points used to answer.
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"annotation":[[610,210],[610,285],[610,360]],"answer":3}
```

### task_charts__style_legend__threshold_series_count / below_threshold_series_count / answer_only / sample 3324060879820023

- `instance_seed`: `3324060879820023`
- `word_count`: `53`
- `body_word_count`: `38`

```text
The plotted figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. At "Land", how many visible series markers are below the threshold value 60?
Answer format: set "answer" to the requested count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__style_legend__x_position_extremum_series_label / x_position_highest_series_label / answer_and_annotation / sample 1082185904652782

- `instance_seed`: `1082185904652782`
- `word_count`: `80`
- `body_word_count`: `37`

```text
The plotted figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Compare the styled series markers at "China". Which legend label is highest?
Required annotation format: set "annotation" to a single [x,y] pixel point at the center of the plotted point used to answer.
Required answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[420,260],"answer":"M7"}
```

### task_charts__style_legend__x_position_extremum_series_label / x_position_highest_series_label / answer_only / sample 1082185904652782

- `instance_seed`: `1082185904652782`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The plotted figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Compare the styled series markers at "China". Which legend label is highest?
Answer field: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"M7"}
```

### task_charts__style_legend__x_position_extremum_series_label / x_position_lowest_series_label / answer_and_annotation / sample 1039712780829013

- `instance_seed`: `1039712780829013`
- `word_count`: `79`
- `body_word_count`: `38`

```text
The figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Use the legend styles to identify the series. At "Minhaj", which series is lowest?
Annotation format: set "annotation" to a single [x,y] pixel point at the center of the plotted point used to answer.
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[420,260],"answer":"M7"}
```

### task_charts__style_legend__x_position_extremum_series_label / x_position_lowest_series_label / answer_only / sample 1039712780829013

- `instance_seed`: `1039712780829013`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The figure shows a scientific line chart where series are identified by legend style, including line pattern, marker shape, and color or grayscale tone. Use the legend styles to identify the series. At "Minhaj", which series is lowest?
Answer field: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"M7"}
```

### task_charts__sunburst__leaf_range_count_under_parent / single / answer_and_annotation / sample 7227647199529178

- `instance_seed`: `7227647199529178`
- `word_count`: `81`
- `body_word_count`: `38`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Within "Alignment", count the outer leaf values from 30 through 35.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[865,244],[945,334],[995,424]],"answer":2}
```

### task_charts__sunburst__leaf_range_count_under_parent / single / answer_only / sample 7227647199529178

- `instance_seed`: `7227647199529178`
- `word_count`: `51`
- `body_word_count`: `38`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Within "Alignment", count the outer leaf values from 30 through 35.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":2}
```

### task_charts__sunburst__leaf_threshold_count_under_parent / above_threshold_leaf_count_under_parent / answer_and_annotation / sample 8196274979187526

- `instance_seed`: `8196274979187526`
- `word_count`: `82`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Under parent category "Throughput", how many outer leaves have values above 33?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[865,244],[945,334],[995,424]],"answer":2}
```

### task_charts__sunburst__leaf_threshold_count_under_parent / above_threshold_leaf_count_under_parent / answer_only / sample 8196274979187526

- `instance_seed`: `8196274979187526`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Under parent category "Throughput", how many outer leaves have values above 33?
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":2}
```

### task_charts__sunburst__leaf_threshold_count_under_parent / below_threshold_leaf_count_under_parent / answer_and_annotation / sample 1608227814048097

- `instance_seed`: `1608227814048097`
- `word_count`: `82`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Count the outer leaves under "Compiler" whose printed values are below 42.
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[865,244],[945,334],[995,424]],"answer":2}
```

### task_charts__sunburst__leaf_threshold_count_under_parent / below_threshold_leaf_count_under_parent / answer_only / sample 1608227814048097

- `instance_seed`: `1608227814048097`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Count the outer leaves under "Compiler" whose printed values are below 42.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"answer":2}
```

### task_charts__sunburst__parent_total_extremum_label / highest_parent_total_label / answer_and_annotation / sample 5419912836937846

- `instance_seed`: `5419912836937846`
- `word_count`: `90`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Which parent category has the greatest sum of printed outer leaf values?
Format for the "annotation" field: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Format for the "answer" field: set "answer" to the exact parent category label.
Example JSON:
{"annotation":[[865,244],[945,334],[445,534]],"answer":"Ablation"}
```

### task_charts__sunburst__parent_total_extremum_label / highest_parent_total_label / answer_only / sample 5419912836937846

- `instance_seed`: `5419912836937846`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Which parent category has the greatest sum of printed outer leaf values?
Final answer format: set "answer" to the exact parent category label.
Example JSON:
{"answer":"Ablation"}
```

### task_charts__sunburst__parent_total_extremum_label / lowest_parent_total_label / answer_and_annotation / sample 4245991832072729

- `instance_seed`: `4245991832072729`
- `word_count`: `86`
- `body_word_count`: `40`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Compare parent-category totals from their outer leaf values. Which parent category is lowest?
Annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Final answer format: set "answer" to the exact parent category label.
Example JSON:
{"annotation":[[865,244],[945,334],[445,534]],"answer":"Ablation"}
```

### task_charts__sunburst__parent_total_extremum_label / lowest_parent_total_label / answer_only / sample 4245991832072729

- `instance_seed`: `4245991832072729`
- `word_count`: `57`
- `body_word_count`: `40`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. Compare parent-category totals from their outer leaf values. Which parent category is lowest?
Format for the "answer" field: set "answer" to the exact parent category label.
Example JSON:
{"answer":"Ablation"}
```

### task_charts__sunburst__parent_total_value / single / answer_and_annotation / sample 4184804063447032

- `instance_seed`: `4184804063447032`
- `word_count`: `84`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. For "Sketch", compute the total from all of its outer leaf values.
Required annotation format: set "annotation" to an array of [x,y] pixel points at the centers of the printed outer leaf values used to answer.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[885,264],[955,326],[995,404]],"answer":105}
```

### task_charts__sunburst__parent_total_value / single / answer_only / sample 4184804063447032

- `instance_seed`: `4184804063447032`
- `word_count`: `52`
- `body_word_count`: `39`

```text
The image shows a not-to-scale concentric hierarchy chart with parent categories in the inner ring, subgroups in the middle ring, and outer leaves with printed integer values. For "Sketch", compute the total from all of its outer leaf values.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":105}
```

### task_charts__surface_3d__panel_variation_label / single / answer_and_annotation / sample 1104911736497720

- `instance_seed`: `1104911736497720`
- `word_count`: `59`
- `body_word_count`: `19`

```text
The plotted figure shows a synthetic 3D chart. Which small 3D chart panel shows the largest z-axis value range?
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the selected panel.
Required answer format: set "answer" to the exact visible panel label as a string.
Example JSON:
{"annotation":[144,116,438,352],"answer":"Trade"}
```

### task_charts__surface_3d__panel_variation_label / single / answer_only / sample 1104911736497720

- `instance_seed`: `1104911736497720`
- `word_count`: `36`
- `body_word_count`: `32`

```text
The plotted figure shows a synthetic 3D chart. Which small 3D chart panel shows the largest z-axis value range?
Answer field: set "answer" to the exact visible panel label as a string.
Example JSON:
{"answer":"Trade"}
```

### task_charts__surface_3d__reference_nearest_label / single / answer_and_annotation / sample 2059477720816303

- `instance_seed`: `2059477720816303`
- `word_count`: `56`
- `body_word_count`: `18`

```text
The plotted figure shows a synthetic 3D chart. Which point is closest to 61 on the "y-axis" axis?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected point marker.
Answer format: set "answer" to the exact visible point label as a string.
Example JSON:
{"annotation":[343,223],"answer":"Haidon"}
```

### task_charts__surface_3d__reference_nearest_label / single / answer_only / sample 2059477720816303

- `instance_seed`: `2059477720816303`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The plotted figure shows a synthetic 3D chart. Which point is closest to 61 on the "y-axis" axis?
Answer field: set "answer" to the exact visible point label as a string.
Example JSON:
{"answer":"Haidon"}
```

### task_charts__surface_3d__series_trend_label / decrease / answer_and_annotation / sample 8951223925899396

- `instance_seed`: `8951223925899396`
- `word_count`: `67`
- `body_word_count`: `23`

```text
The figure shows a synthetic 3D chart. Which labeled series decreases the most in z-axis value between the first and last x-axis positions?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] connecting the first and last marker centers of the answer series.
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[[229,235],[599,369]],"answer":"Davin"}
```

### task_charts__surface_3d__series_trend_label / decrease / answer_only / sample 8951223925899396

- `instance_seed`: `8951223925899396`
- `word_count`: `40`
- `body_word_count`: `23`

```text
The figure shows a synthetic 3D chart. Which labeled series decreases the most in z-axis value between the first and last x-axis positions?
Answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"Davin"}
```

### task_charts__surface_3d__series_trend_label / increase / answer_and_annotation / sample 3572734093323229

- `instance_seed`: `3572734093323229`
- `word_count`: `68`
- `body_word_count`: `22`

```text
The image shows a synthetic 3D chart. From the first x-axis position to the last, which series has the strongest z-axis increase?
Required annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] connecting the first and last marker centers of the answer series.
Required answer format: set "answer" to the exact visible series label as a string.
Example JSON:
{"annotation":[[229,369],[599,235]],"answer":"Davin"}
```

### task_charts__surface_3d__series_trend_label / increase / answer_only / sample 3572734093323229

- `instance_seed`: `3572734093323229`
- `word_count`: `42`
- `body_word_count`: `22`

```text
The image shows a synthetic 3D chart. From the first x-axis position to the last, which series has the strongest z-axis increase?
Format for the "answer" field: set "answer" to the exact visible series label as a string.
Example JSON:
{"answer":"Davin"}
```

### task_charts__table__absolute_difference_between_rows_over_year_interval / single / answer_and_annotation / sample 3299108592775174

- `instance_seed`: `3299108592775174`
- `word_count`: `96`
- `body_word_count`: `44`

```text
The image shows a table with one Name column and several year columns in chronological order. Add the values for "Av" from 2010 to 2013, then add the values for "Hawk" over the same years. What is the non-negative difference between the two totals?
Annotation format: set "annotation" to an object mapping each queried row label to one [x0,y0,x1,y1] box surrounding that row span across the queried year interval.
Answer format: set "answer" to the exact integer result.
Example JSON:
{"annotation":{"Av":[260,180,444,220],"Hawk":[260,236,444,276]},"answer":7}
```

### task_charts__table__absolute_difference_between_rows_over_year_interval / single / answer_only / sample 3299108592775174

- `instance_seed`: `3299108592775174`
- `word_count`: `58`
- `body_word_count`: `44`

```text
The image shows a table with one Name column and several year columns in chronological order. Add the values for "Av" from 2010 to 2013, then add the values for "Hawk" over the same years. What is the non-negative difference between the two totals?
Required answer format: set "answer" to the exact integer result.
Example JSON:
{"answer":7}
```

### task_charts__table__categorical_value_count / single / answer_and_annotation / sample 4551015087251839

- `instance_seed`: `4551015087251839`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. How many entries in the "Pearl" column are "Slate"?
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] boxes around every matching table cell, or [] if none match.
Format for the "answer" field: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[260,180,372,236],[260,292,372,348]],"answer":2}
```

### task_charts__table__categorical_value_count / single / answer_only / sample 4551015087251839

- `instance_seed`: `4551015087251839`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. How many entries in the "Pearl" column are "Slate"?
Answer format: set "answer" to the exact count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__table__column_rank_label / highest_rank_in_column / answer_and_annotation / sample 3979241272456719

- `instance_seed`: `3979241272456719`
- `word_count`: `69`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Identify the row with the 3rd highest "Qatar" value.
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] box around the answer row cell in the queried column.
Format for the "answer" field: set "answer" to the exact row label as a string.
Example JSON:
{"annotation":[260,180,372,236],"answer":"Ava"}
```

### task_charts__table__column_rank_label / highest_rank_in_column / answer_only / sample 3979241272456719

- `instance_seed`: `3979241272456719`
- `word_count`: `38`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Identify the row with the 3rd highest "Qatar" value.
Answer format: set "answer" to the exact row label as a string.
Example JSON:
{"answer":"Ava"}
```

### task_charts__table__column_rank_label / lowest_rank_in_column / answer_and_annotation / sample 7526100962589752

- `instance_seed`: `7526100962589752`
- `word_count`: `63`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Identify the row with the 3rd lowest "Park" value.
Annotation format: set "annotation" to one [x0,y0,x1,y1] box around the answer row cell in the queried column.
Answer format: set "answer" to the exact row label as a string.
Example JSON:
{"annotation":[260,180,372,236],"answer":"Ava"}
```

### task_charts__table__column_rank_label / lowest_rank_in_column / answer_only / sample 7526100962589752

- `instance_seed`: `7526100962589752`
- `word_count`: `41`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Identify the row with the 3rd lowest "Park" value.
Format for the "answer" field: set "answer" to the exact row label as a string.
Example JSON:
{"answer":"Ava"}
```

### task_charts__table__column_summary_value / column_mean / answer_and_annotation / sample 2647113680896034

- `instance_seed`: `2647113680896034`
- `word_count`: `64`
- `body_word_count`: `24`

```text
The image shows a table with one Name column and several data columns. What is the mean of the values in the "Fiji" column?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] box around the queried column values.
Format for the "answer" field: set "answer" to the exact integer result.
Example JSON:
{"annotation":[260,180,372,520],"answer":14}
```

### task_charts__table__column_summary_value / column_mean / answer_only / sample 2647113680896034

- `instance_seed`: `2647113680896034`
- `word_count`: `40`
- `body_word_count`: `24`

```text
The image shows a table with one Name column and several data columns. What is the mean of the values in the "Fiji" column?
Format for the "answer" field: set "answer" to the exact integer result.
Example JSON:
{"answer":14}
```

### task_charts__table__column_summary_value / column_median / answer_and_annotation / sample 1920923777885773

- `instance_seed`: `1920923777885773`
- `word_count`: `54`
- `body_word_count`: `20`

```text
The image shows a table with one Name column and several data columns. Compute the median of the "Nakeem" column.
Annotation format: set "annotation" to one [x0,y0,x1,y1] box around the queried column values.
Answer format: set "answer" to the exact integer result.
Example JSON:
{"annotation":[260,180,372,520],"answer":13}
```

### task_charts__table__column_summary_value / column_median / answer_only / sample 1920923777885773

- `instance_seed`: `1920923777885773`
- `word_count`: `34`
- `body_word_count`: `20`

```text
The image shows a table with one Name column and several data columns. Compute the median of the "Nakeem" column.
Final answer format: set "answer" to the exact integer result.
Example JSON:
{"answer":13}
```

### task_charts__table__column_summary_value / column_sum / answer_and_annotation / sample 4441767026255521

- `instance_seed`: `4441767026255521`
- `word_count`: `53`
- `body_word_count`: `19`

```text
The image shows a table with one Name column and several data columns. Determine the column sum for "Lanaya".
Annotation format: set "annotation" to one [x0,y0,x1,y1] box around the queried column values.
Answer field: set "answer" to the exact integer result.
Example JSON:
{"annotation":[260,180,372,520],"answer":84}
```

### task_charts__table__column_summary_value / column_sum / answer_only / sample 4441767026255521

- `instance_seed`: `4441767026255521`
- `word_count`: `33`
- `body_word_count`: `19`

```text
The image shows a table with one Name column and several data columns. Determine the column sum for "Lanaya".
Final answer format: set "answer" to the exact integer result.
Example JSON:
{"answer":84}
```

### task_charts__table__filtered_column_mean / above_threshold_filtered_mean / answer_and_annotation / sample 7965930273028578

- `instance_seed`: `7965930273028578`
- `word_count`: `86`
- `body_word_count`: `29`

```text
The image shows a table with one Name column and several data columns. What is the average of the "Truist" values for rows where "Bce" is greater than 3?
Annotation format: set "annotation" to an object with "filter_cells" and "target_cells", each mapping to arrays of [x0,y0,x1,y1] boxes for the selected rows.
Answer format: set "answer" to the exact integer result.
Example JSON:
{"annotation":{"filter_cells":[[260,180,372,236],[260,236,372,292]],"target_cells":[[374,180,486,236],[374,236,486,292]]},"answer":14}
```

### task_charts__table__filtered_column_mean / above_threshold_filtered_mean / answer_only / sample 7965930273028578

- `instance_seed`: `7965930273028578`
- `word_count`: `45`
- `body_word_count`: `29`

```text
The image shows a table with one Name column and several data columns. What is the average of the "Truist" values for rows where "Bce" is greater than 3?
Format for the "answer" field: set "answer" to the exact integer result.
Example JSON:
{"answer":14}
```

### task_charts__table__filtered_column_mean / below_threshold_filtered_mean / answer_and_annotation / sample 4350213766203192

- `instance_seed`: `4350213766203192`
- `word_count`: `86`
- `body_word_count`: `29`

```text
The image shows a table with one Name column and several data columns. What is the average of the "PHCI" values for rows where "BREZU" is less than 27?
Annotation format: set "annotation" to an object with "filter_cells" and "target_cells", each mapping to arrays of [x0,y0,x1,y1] boxes for the selected rows.
Answer field: set "answer" to the exact integer result.
Example JSON:
{"annotation":{"filter_cells":[[260,180,372,236],[260,236,372,292]],"target_cells":[[374,180,486,236],[374,236,486,292]]},"answer":14}
```

### task_charts__table__filtered_column_mean / below_threshold_filtered_mean / answer_only / sample 4350213766203192

- `instance_seed`: `4350213766203192`
- `word_count`: `43`
- `body_word_count`: `29`

```text
The image shows a table with one Name column and several data columns. What is the average of the "PHCI" values for rows where "BREZU" is less than 27?
Final answer format: set "answer" to the exact integer result.
Example JSON:
{"answer":14}
```

### task_charts__table__filtered_column_mean / interval_filtered_mean / answer_and_annotation / sample 7206531269978768

- `instance_seed`: `7206531269978768`
- `word_count`: `94`
- `body_word_count`: `31`

```text
The image shows a table with one Name column and several data columns. What is the average of the "Canada" values for rows where "Rwanda" is from 21 to 27 inclusive?
Format for the "annotation" field: set "annotation" to an object with "filter_cells" and "target_cells", each mapping to arrays of [x0,y0,x1,y1] boxes for the selected rows.
Format for the "answer" field: set "answer" to the exact integer result.
Example JSON:
{"annotation":{"filter_cells":[[260,180,372,236],[260,236,372,292]],"target_cells":[[374,180,486,236],[374,236,486,292]]},"answer":14}
```

### task_charts__table__filtered_column_mean / interval_filtered_mean / answer_only / sample 7206531269978768

- `instance_seed`: `7206531269978768`
- `word_count`: `47`
- `body_word_count`: `31`

```text
The image shows a table with one Name column and several data columns. What is the average of the "Canada" values for rows where "Rwanda" is from 21 to 27 inclusive?
Format for the "answer" field: set "answer" to the exact integer result.
Example JSON:
{"answer":14}
```

### task_charts__table__interval_value_count / single / answer_and_annotation / sample 6469605999077859

- `instance_seed`: `6469605999077859`
- `word_count`: `81`
- `body_word_count`: `25`

```text
The image shows a table with one Name column and several data columns. Find the number of rows with "Jerret" values in [26, 31], inclusive.
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] boxes around every matching table cell, or [] if none match.
Format for the "answer" field: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[260,180,372,236],[260,236,372,292],[260,292,372,348]],"answer":3}
```

### task_charts__table__interval_value_count / single / answer_only / sample 6469605999077859

- `instance_seed`: `6469605999077859`
- `word_count`: `43`
- `body_word_count`: `25`

```text
The image shows a table with one Name column and several data columns. Find the number of rows with "Jerret" values in [26, 31], inclusive.
Format for the "answer" field: set "answer" to the exact count as an integer.
Example JSON:
{"answer":3}
```

### task_charts__table__sum_absolute_differences_between_rows_over_year_interval / single / answer_and_annotation / sample 101130493383919

- `instance_seed`: `101130493383919`
- `word_count`: `104`
- `body_word_count`: `41`

```text
The image shows a table with one Name column and several year columns in chronological order. For rows "Hui" and "Etz", compare the two rows year by year from 2009 through 2012. What is the sum of the absolute yearly differences?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes for the queried year cells from both named rows across the interval.
Answer field: set "answer" to the exact integer result.
Example JSON:
{"annotation":[[260,180,320,220],[322,180,382,220],[384,180,444,220],[260,236,320,276],[322,236,382,276],[384,236,444,276]],"answer":17}
```

### task_charts__table__sum_absolute_differences_between_rows_over_year_interval / single / answer_only / sample 101130493383919

- `instance_seed`: `101130493383919`
- `word_count`: `55`
- `body_word_count`: `41`

```text
The image shows a table with one Name column and several year columns in chronological order. For rows "Hui" and "Etz", compare the two rows year by year from 2009 through 2012. What is the sum of the absolute yearly differences?
Required answer format: set "answer" to the exact integer result.
Example JSON:
{"answer":17}
```

### task_charts__table__threshold_count / above_threshold_count / answer_and_annotation / sample 2667384428595832

- `instance_seed`: `2667384428595832`
- `word_count`: `70`
- `body_word_count`: `24`

```text
The image shows a table with one Name column and several data columns. Find the number of rows with "Brinya" values greater than 1.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around every matching table cell, or [] if none match.
Answer format: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[260,180,372,236],[260,236,372,292]],"answer":2}
```

### task_charts__table__threshold_count / above_threshold_count / answer_only / sample 2667384428595832

- `instance_seed`: `2667384428595832`
- `word_count`: `39`
- `body_word_count`: `24`

```text
The image shows a table with one Name column and several data columns. Find the number of rows with "Brinya" values greater than 1.
Answer format: set "answer" to the exact count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__table__threshold_count / below_threshold_count / answer_and_annotation / sample 3184619982825503

- `instance_seed`: `3184619982825503`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Determine how many rows show "Analis" less than 28.
Format for the "annotation" field: set "annotation" to an array of [x0,y0,x1,y1] boxes around every matching table cell, or [] if none match.
Format for the "answer" field: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[260,180,372,236],[260,236,372,292]],"answer":2}
```

### task_charts__table__threshold_count / below_threshold_count / answer_only / sample 3184619982825503

- `instance_seed`: `3184619982825503`
- `word_count`: `40`
- `body_word_count`: `22`

```text
The image shows a table with one Name column and several data columns. Determine how many rows show "Analis" less than 28.
Format for the "answer" field: set "answer" to the exact count as an integer.
Example JSON:
{"answer":2}
```

### task_charts__treemap__group_total_value / single / answer_and_annotation / sample 5707944866847289

- `instance_seed`: `5707944866847289`
- `word_count`: `82`
- `body_word_count`: `33`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Use the child rectangles belonging to parent category "Council". What is their combined value?
Required annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around the child rectangles inside the requested parent rectangle.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[142,150,198,210],[204,216,268,286],[300,300,370,372]],"answer":168}
```

### task_charts__treemap__group_total_value / single / answer_only / sample 5707944866847289

- `instance_seed`: `5707944866847289`
- `word_count`: `46`
- `body_word_count`: `33`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Use the child rectangles belonging to parent category "Council". What is their combined value?
Final answer format: set "answer" to the requested integer.
Example JSON:
{"answer":168}
```

### task_charts__treemap__parent_total_extremum_label / largest_parent_total / answer_and_annotation / sample 2956152590321809

- `instance_seed`: `2956152590321809`
- `word_count`: `84`
- `body_word_count`: `30`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Compare the totals of all parent categories. Which one is largest?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around every child rectangle inside the answer parent rectangle.
Final answer format: set "answer" to the exact visible parent category label as a string.
Example JSON:
{"annotation":[[142,150,198,210],[204,216,268,286],[300,300,370,372]],"answer":"Housing"}
```

### task_charts__treemap__parent_total_extremum_label / largest_parent_total / answer_only / sample 2956152590321809

- `instance_seed`: `2956152590321809`
- `word_count`: `49`
- `body_word_count`: `30`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Compare the totals of all parent categories. Which one is largest?
Required answer format: set "answer" to the exact visible parent category label as a string.
Example JSON:
{"answer":"Housing"}
```

### task_charts__treemap__parent_total_extremum_label / smallest_parent_total / answer_and_annotation / sample 256163007485181

- `instance_seed`: `256163007485181`
- `word_count`: `85`
- `body_word_count`: `32`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Sum each parent category's child values. Which parent category has the smallest total?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around every child rectangle inside the answer parent rectangle.
Answer field: set "answer" to the exact visible parent category label as a string.
Example JSON:
{"annotation":[[142,150,198,210],[204,216,268,286],[300,300,370,372]],"answer":"Housing"}
```

### task_charts__treemap__parent_total_extremum_label / smallest_parent_total / answer_only / sample 256163007485181

- `instance_seed`: `256163007485181`
- `word_count`: `51`
- `body_word_count`: `32`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Sum each parent category's child values. Which parent category has the smallest total?
Final answer format: set "answer" to the exact visible parent category label as a string.
Example JSON:
{"answer":"Housing"}
```

### task_charts__treemap__repeated_leaf_aggregate_value / treemap_repeated_leaf_average_value / answer_and_annotation / sample 2208928352417811

- `instance_seed`: `2208928352417811`
- `word_count`: `79`
- `body_word_count`: `33`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Find every child rectangle labeled "Adults". What is the average of their printed values?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around the matching child rectangles across parent rectangles.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[142,150,198,210],[404,150,468,210],[672,150,738,210]],"answer":54}
```

### task_charts__treemap__repeated_leaf_aggregate_value / treemap_repeated_leaf_average_value / answer_only / sample 2208928352417811

- `instance_seed`: `2208928352417811`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Find every child rectangle labeled "Adults". What is the average of their printed values?
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":54}
```

### task_charts__treemap__repeated_leaf_aggregate_value / treemap_repeated_leaf_sum_value / answer_and_annotation / sample 2601984679393205

- `instance_seed`: `2601984679393205`
- `word_count`: `76`
- `body_word_count`: `30`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Using all parent rectangles, sum the values of child label "Reptiles".
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] boxes around the matching child rectangles across parent rectangles.
Answer field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[142,150,198,210],[404,150,468,210],[672,150,738,210]],"answer":54}
```

### task_charts__treemap__repeated_leaf_aggregate_value / treemap_repeated_leaf_sum_value / answer_only / sample 2601984679393205

- `instance_seed`: `2601984679393205`
- `word_count`: `45`
- `body_word_count`: `30`

```text
The image shows a treemap composition chart with parent category rectangles and child rectangles labeled with printed integer values. Using all parent rectangles, sum the values of child label "Reptiles".
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"answer":54}
```

### task_charts__uncertainty_band__band_overlap_count / single / answer_and_annotation / sample 6831917226057468

- `instance_seed`: `6831917226057468`
- `word_count`: `76`
- `body_word_count`: `35`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. For how many labeled x positions do the two shaded uncertainty bands overlap?
Required annotation format: set "annotation" to an array of [x,y] pixel points, one centered inside each counted overlap region.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[345,318],[512,286],[679,302]],"answer":3}
```

### task_charts__uncertainty_band__band_overlap_count / single / answer_only / sample 6831917226057468

- `instance_seed`: `6831917226057468`
- `word_count`: `49`
- `body_word_count`: `35`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. For how many labeled x positions do the two shaded uncertainty bands overlap?
Final answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":3}
```

### task_charts__uncertainty_band__band_width_extremum_x_label / narrowest_band_x_label / answer_and_annotation / sample 4349553421510754

- `instance_seed`: `4349553421510754`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. Using band width from lower boundary to upper boundary, which x-axis label is narrowest for "Juris"?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the lower band boundary to the upper band boundary at the answer x-axis label.
Answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[[612,382],[612,214]],"answer":"FY24"}
```

### task_charts__uncertainty_band__band_width_extremum_x_label / narrowest_band_x_label / answer_only / sample 4349553421510754

- `instance_seed`: `4349553421510754`
- `word_count`: `58`
- `body_word_count`: `38`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. Using band width from lower boundary to upper boundary, which x-axis label is narrowest for "Juris"?
Format for the "answer" field: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"FY24"}
```

### task_charts__uncertainty_band__band_width_extremum_x_label / widest_band_x_label / answer_and_annotation / sample 2675368628324004

- `instance_seed`: `2675368628324004`
- `word_count`: `84`
- `body_word_count`: `35`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. Look only at series "Vyvian". What x-axis label has the widest uncertainty band?
Annotation format: set "annotation" to one segment [[x0,y0],[x1,y1]] from the lower band boundary to the upper band boundary at the answer x-axis label.
Final answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"annotation":[[612,382],[612,214]],"answer":"FY24"}
```

### task_charts__uncertainty_band__band_width_extremum_x_label / widest_band_x_label / answer_only / sample 2675368628324004

- `instance_seed`: `2675368628324004`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The image shows a line chart with two labeled series, each shown with a central line and a shaded upper-to-lower uncertainty band. Look only at series "Vyvian". What x-axis label has the widest uncertainty band?
Answer format: set "answer" to the exact visible x-axis label as a string.
Example JSON:
{"answer":"FY24"}
```

### task_charts__violin__modality_label / single / answer_and_annotation / sample 4964401253633569

- `instance_seed`: `4964401253633569`
- `word_count`: `76`
- `body_word_count`: `35`

```text
The image shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Identify the violin plot that has two distinct density peaks.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the winning violin plot.
Answer field: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"annotation":[240,140,330,520],"answer":"H9H3"}
```

### task_charts__violin__modality_label / single / answer_only / sample 4964401253633569

- `instance_seed`: `4964401253633569`
- `word_count`: `55`
- `body_word_count`: `35`

```text
The image shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Identify the violin plot that has two distinct density peaks.
Required answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"answer":"H9H3"}
```

### task_charts__violin__mode_extremum_label / highest_mode / answer_and_annotation / sample 3213588102366173

- `instance_seed`: `3213588102366173`
- `word_count`: `83`
- `body_word_count`: `36`

```text
The image shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Which label has the highest density peak on the vertical axis?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] pixel box around the winning violin plot.
Format for the "answer" field: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"annotation":[240,140,330,520],"answer":"H9H3"}
```

### task_charts__violin__mode_extremum_label / highest_mode / answer_only / sample 3213588102366173

- `instance_seed`: `3213588102366173`
- `word_count`: `55`
- `body_word_count`: `36`

```text
The image shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Which label has the highest density peak on the vertical axis?
Answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"answer":"H9H3"}
```

### task_charts__violin__mode_extremum_label / lowest_mode / answer_and_annotation / sample 7377107756644269

- `instance_seed`: `7377107756644269`
- `word_count`: `76`
- `body_word_count`: `33`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Identify the label with the lowermost density peak.
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the winning violin plot.
Required answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"annotation":[240,140,330,520],"answer":"H9H3"}
```

### task_charts__violin__mode_extremum_label / lowest_mode / answer_only / sample 7377107756644269

- `instance_seed`: `7377107756644269`
- `word_count`: `55`
- `body_word_count`: `33`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Identify the label with the lowermost density peak.
Format for the "answer" field: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"answer":"H9H3"}
```

### task_charts__violin__support_width_extremum_label / narrowest_support / answer_and_annotation / sample 5627322095454363

- `instance_seed`: `5627322095454363`
- `word_count`: `76`
- `body_word_count`: `34`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Find the violin plot with the narrowest support range.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the winning violin plot.
Final answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"annotation":[240,140,330,520],"answer":"H9H3"}
```

### task_charts__violin__support_width_extremum_label / narrowest_support / answer_only / sample 5627322095454363

- `instance_seed`: `5627322095454363`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Find the violin plot with the narrowest support range.
Answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"answer":"H9H3"}
```

### task_charts__violin__support_width_extremum_label / widest_support / answer_and_annotation / sample 2519530910847394

- `instance_seed`: `2519530910847394`
- `word_count`: `75`
- `body_word_count`: `32`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Which label has the largest bottom-to-top range?
Required annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the winning violin plot.
Required answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"annotation":[240,140,330,520],"answer":"H9H3"}
```

### task_charts__violin__support_width_extremum_label / widest_support / answer_only / sample 2519530910847394

- `instance_seed`: `2519530910847394`
- `word_count`: `52`
- `body_word_count`: `32`

```text
The chart shows a set of labeled violin plots. Wider parts of each shape show where that label's values are denser on the vertical axis. Which label has the largest bottom-to-top range?
Final answer format: set "answer" to the exact visible label string of the requested violin plot.
Example JSON:
{"answer":"H9H3"}
```

### task_charts__waterfall__remove_step_final_total / single / answer_and_annotation / sample 5214074899876930

- `instance_seed`: `5214074899876930`
- `word_count`: `86`
- `body_word_count`: `35`

```text
The chart shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. The final bar includes every signed contribution. If "Boli" were removed, what final total would result?
Annotation format: set "annotation" to an object mapping "final_total_bar" and "target_contribution_bar" to [x0,y0,x1,y1] pixel boxes around the full waterfall bars.
Final answer format: set "answer" to the counterfactual final total as an integer.
Example JSON:
{"annotation":{"final_total_bar":[[960,210,1038,610]],"target_contribution_bar":[[370,318,438,512]]},"answer":57}
```

### task_charts__waterfall__remove_step_final_total / single / answer_only / sample 5214074899876930

- `instance_seed`: `5214074899876930`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The chart shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. The final bar includes every signed contribution. If "Boli" were removed, what final total would result?
Final answer format: set "answer" to the counterfactual final total as an integer.
Example JSON:
{"answer":57}
```

### task_charts__waterfall__reverse_step_final_total / single / answer_and_annotation / sample 5749030100348895

- `instance_seed`: `5749030100348895`
- `word_count`: `89`
- `body_word_count`: `37`

```text
The visual shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Reverse the sign of contribution "2014" while keeping all other contributions the same. What is the final total?
Required annotation format: set "annotation" to an object mapping "final_total_bar" and "target_contribution_bar" to [x0,y0,x1,y1] pixel boxes around the full waterfall bars.
Required answer format: set "answer" to the counterfactual final total as an integer.
Example JSON:
{"annotation":{"final_total_bar":[[960,210,1038,610]],"target_contribution_bar":[[370,318,438,512]]},"answer":57}
```

### task_charts__waterfall__reverse_step_final_total / single / answer_only / sample 5749030100348895

- `instance_seed`: `5749030100348895`
- `word_count`: `53`
- `body_word_count`: `49`

```text
The visual shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Reverse the sign of contribution "2014" while keeping all other contributions the same. What is the final total?
Answer field: set "answer" to the counterfactual final total as an integer.
Example JSON:
{"answer":57}
```

### task_charts__waterfall__running_total_extremum_value / maximum_running_total / answer_and_annotation / sample 4601185398736365

- `instance_seed`: `4601185398736365`
- `word_count`: `83`
- `body_word_count`: `36`

```text
The figure shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Ignoring the summary final bar, scan the start and contribution bars. What is the highest running total?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full start or contribution bar where that cumulative total is reached.
Final answer format: set "answer" to the requested cumulative total as an integer.
Example JSON:
{"annotation":[292,218,366,610],"answer":76}
```

### task_charts__waterfall__running_total_extremum_value / maximum_running_total / answer_only / sample 4601185398736365

- `instance_seed`: `4601185398736365`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The figure shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Ignoring the summary final bar, scan the start and contribution bars. What is the highest running total?
Final answer format: set "answer" to the requested cumulative total as an integer.
Example JSON:
{"answer":76}
```

### task_charts__waterfall__running_total_extremum_value / minimum_running_total / answer_and_annotation / sample 263886441588688

- `instance_seed`: `263886441588688`
- `word_count`: `88`
- `body_word_count`: `36`

```text
The image contains a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Ignoring the summary final bar, scan the start and contribution bars. What is the lowest running total?
Format for the "annotation" field: set "annotation" to one [x0,y0,x1,y1] pixel box around the full start or contribution bar where that cumulative total is reached.
Format for the "answer" field: set "answer" to the requested cumulative total as an integer.
Example JSON:
{"annotation":[292,218,366,610],"answer":76}
```

### task_charts__waterfall__running_total_extremum_value / minimum_running_total / answer_only / sample 263886441588688

- `instance_seed`: `263886441588688`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The image contains a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. Ignoring the summary final bar, scan the start and contribution bars. What is the lowest running total?
Required answer format: set "answer" to the requested cumulative total as an integer.
Example JSON:
{"answer":76}
```

### task_charts__waterfall__running_total_value / single / answer_and_annotation / sample 2306324507705143

- `instance_seed`: `2306324507705143`
- `word_count`: `91`
- `body_word_count`: `28`

```text
The visual shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. After applying contribution "Joao", what is the running total?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full waterfall bars from the start bar through the target contribution bar, including the target contribution bar.
Final answer format: set "answer" to the requested running total as an integer.
Example JSON:
{"annotation":[[72,420,132,610],[182,330,242,610],[292,330,366,512]],"answer":57}
```

### task_charts__waterfall__running_total_value / single / answer_only / sample 2306324507705143

- `instance_seed`: `2306324507705143`
- `word_count`: `45`
- `body_word_count`: `28`

```text
The visual shows a waterfall chart with a start bar, signed contribution bars, connector lines, and a final-total bar. After applying contribution "Joao", what is the running total?
Required answer format: set "answer" to the requested running total as an integer.
Example JSON:
{"answer":57}
```
