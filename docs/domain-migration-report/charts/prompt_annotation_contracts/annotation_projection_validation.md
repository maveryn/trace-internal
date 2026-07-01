# Annotation Projection Validation

- sampled instances: `340`
- query ids covered: `340`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 67, 'bbox_map': 4, 'bbox_set': 55, 'bbox_set_map': 5, 'point': 53, 'point_map': 52, 'point_set': 60, 'point_set_map': 2, 'segment': 24, 'segment_set': 18}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
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

## Issues

No issues found.
