# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-29T20:59:38Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `42`
- Tasks: `180`
- Bbox-family runtime tasks: `68`
- Samples inspected: `18000`
- Bboxes inspected: `21449`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| charts | boxplot | `task_charts__boxplot__iqr_extremum_label` | ['bbox'] | 100 | 100 | 24.336 | 37.28 | 24.336 | pass |
| charts | composition_panels | `task_charts__composition_panels__composition_shift_l1_distance` | ['bbox_set'] | 100 | 200 | 299.5 | 228 | 228 | pass |
| charts | composition_panels | `task_charts__composition_panels__conditioned_panel_sum_from_percent` | ['bbox_set'] | 100 | 372 | 299.5 | 228 | 228 | pass |
| charts | composition_panels | `task_charts__composition_panels__segment_count_nearest_target_panel_label` | ['bbox'] | 100 | 100 | 299.5 | 228 | 228 | pass |
| charts | composition_panels | `task_charts__composition_panels__segment_pair_count_gap_extremum_panel_label` | ['bbox'] | 100 | 100 | 299.5 | 228 | 228 | pass |
| charts | composition_panels | `task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count` | ['bbox_set'] | 100 | 258 | 299.5 | 228 | 228 | pass |
| charts | contour_density | `task_charts__contour_density__density_extremum_region_label` | ['bbox'] | 100 | 100 | 315.846 | 164.099 | 164.099 | pass |
| charts | contour_density | `task_charts__contour_density__density_threshold_region_count` | ['bbox_set'] | 100 | 287 | 316.203 | 159.651 | 159.651 | pass |
| charts | contour_density | `task_charts__contour_density__reference_distance_extremum_label` | ['bbox'] | 100 | 100 | 324.199 | 160.185 | 160.185 | pass |
| charts | contour_density | `task_charts__contour_density__spread_extremum_region_label` | ['bbox'] | 100 | 100 | 216.117 | 118.938 | 118.938 | pass |
| charts | heatmap | `task_charts__heatmap__axis_cell_extremum_label` | ['bbox'] | 100 | 100 | 77.166 | 48.6 | 48.6 | pass |
| charts | heatmap | `task_charts__heatmap__axis_condition_extremum_label` | ['bbox_set'] | 100 | 376 | 77.166 | 48.6 | 48.6 | pass |
| charts | heatmap | `task_charts__heatmap__colorbar_interval_cell_count` | ['bbox_set'] | 100 | 753 | 117.75 | 71.142 | 71.142 | pass |
| charts | heatmap | `task_charts__heatmap__colorbar_threshold_cell_count` | ['bbox_set'] | 100 | 861 | 117.75 | 71.142 | 71.142 | pass |
| charts | heatmap | `task_charts__heatmap__condition_run_extremum_label` | ['bbox_set'] | 100 | 271 | 77.166 | 48.6 | 48.6 | pass |
| charts | histogram | `task_charts__histogram__cumulative_rank_bin_label` | ['bbox'] | 100 | 100 | 35.1 | 25.04 | 25.04 | pass |
| charts | histogram | `task_charts__histogram__interval_mass` | ['bbox_set'] | 100 | 1083 | 35.1 | 25.04 | 25.04 | pass |
| charts | matrix | `task_charts__matrix__axis_extremum_label` | ['bbox_set'] | 100 | 603 | 84 | 44.833 | 44.833 | pass |
| charts | matrix | `task_charts__matrix__off_diagonal_confusion_label` | ['bbox_set'] | 100 | 788 | 85.833 | 46.666 | 46.666 | pass |
| charts | matrix | `task_charts__matrix__threshold_cell_count` | ['bbox_set'] | 100 | 488 | 84 | 44.833 | 44.833 | pass |
| charts | pictogram | `task_charts__pictogram__category_total_extremum_label` | ['bbox'] | 100 | 100 | 784 | 54.6 | 54.6 | pass |
| charts | pictogram | `task_charts__pictogram__category_total_value` | ['bbox'] | 100 | 100 | 784 | 54.4 | 54.4 | pass |
| charts | pictogram | `task_charts__pictogram__group_difference_value` | ['bbox_map'] | 100 | 200 | 786 | 54.6 | 54.6 | pass |
| charts | pictogram | `task_charts__pictogram__target_value_nearest_category_label` | ['bbox'] | 100 | 100 | 784 | 54.4 | 54.4 | pass |
| charts | pictogram | `task_charts__pictogram__threshold_count` | ['bbox_set'] | 100 | 292 | 784 | 54.4 | 54.4 | pass |
| charts | population_pyramid | `task_charts__population_pyramid__age_group_threshold_count` | ['bbox_set'] | 100 | 537 | 72.758 | 46 | 46 | pass |
| charts | population_pyramid | `task_charts__population_pyramid__dominant_side_count` | ['bbox_set'] | 100 | 503 | 123.749 | 46 | 46 | pass |
| charts | population_pyramid | `task_charts__population_pyramid__side_gap_extremum_label` | ['bbox'] | 100 | 100 | 104.138 | 46 | 46 | pass |
| charts | population_pyramid | `task_charts__population_pyramid__side_value_extremum_label` | ['bbox'] | 100 | 100 | 31.379 | 36 | 31.379 | pass |
| charts | radar | `task_charts__radar__highlighted_metric_threshold_panel_count` | ['bbox_set'] | 100 | 370 | 437.333 | 244.666 | 244.666 | pass |
| charts | radar | `task_charts__radar__matching_condition_panel_count` | ['bbox_set'] | 100 | 339 | 322.5 | 244.666 | 244.666 | pass |
| charts | radial_progress | `task_charts__radial_progress__extremum_remaining_label` | ['bbox'] | 100 | 100 | 230.4 | 233.333 | 230.4 | pass |
| charts | radial_progress | `task_charts__radial_progress__progress_interval_count` | ['bbox_set'] | 100 | 318 | 230.4 | 233.333 | 230.4 | pass |
| charts | radial_progress | `task_charts__radial_progress__progress_threshold_count` | ['bbox_set'] | 100 | 298 | 230.4 | 233.333 | 230.4 | pass |
| charts | radial_sankey | `task_charts__radial_sankey__dominant_endpoint_label` | ['bbox'] | 100 | 100 | 78 | 50 | 50 | pass |
| charts | radial_sankey | `task_charts__radial_sankey__transfer_total_value` | ['bbox_set'] | 100 | 200 | 38 | 28 | 28 | pass |
| charts | region_map | `task_charts__region_map__adjacent_category_count` | ['bbox_set'] | 100 | 377 | 90.63 | 43.756 | 43.756 | pass |
| charts | region_map | `task_charts__region_map__adjacent_numeric_threshold_count` | ['bbox_set'] | 100 | 344 | 84.579 | 44.908 | 44.908 | pass |
| charts | region_map | `task_charts__region_map__adjacent_same_category_count` | ['bbox_set'] | 100 | 336 | 80.856 | 43.739 | 43.739 | pass |
| charts | region_map | `task_charts__region_map__named_region_set_total_value` | ['bbox_set'] | 100 | 401 | 98.213 | 45.705 | 45.705 | pass |
| charts | scatter_cluster | `task_charts__scatter_cluster__cluster_area_rank_label` | ['bbox'] | 100 | 100 | 105.34 | 73.17 | 73.17 | pass |
| charts | scatter_cluster | `task_charts__scatter_cluster__cluster_spread_extremum_label` | ['bbox'] | 100 | 100 | 67.117 | 55.867 | 55.867 | pass |
| charts | scatter_cluster | `task_charts__scatter_cluster__cluster_trend_direction_label` | ['bbox'] | 100 | 100 | 215.406 | 160.766 | 160.766 | pass |
| charts | scatter_points | `task_charts__scatter_points__category_axis_mean_extremum_label` | ['bbox'] | 100 | 100 | 52.897 | 49.849 | 49.849 | pass |
| charts | scatter_readout | `task_charts__scatter_readout__series_x_extremum_label` | ['bbox_map', 'point'] | 100 | 0 |  |  |  | pass |
| charts | size_encoding | `task_charts__size_encoding__category_relative_size_count` | ['bbox_set_map'] | 100 | 345 | 50.8 | 24.5 | 24.5 | pass |
| charts | size_encoding | `task_charts__size_encoding__filtered_item_extremum_label` | ['bbox'] | 100 | 100 | 57.373 | 24.5 | 24.5 | pass |
| charts | size_encoding | `task_charts__size_encoding__global_item_extremum_category_label` | ['bbox'] | 100 | 100 | 43 | 24.5 | 24.5 | pass |
| charts | size_encoding | `task_charts__size_encoding__panel_category_extremum_panel_label` | ['bbox'] | 100 | 100 | 47.678 | 47.678 | 47.678 | pass |
| charts | surface_3d | `task_charts__surface_3d__panel_variation_label` | ['bbox'] | 100 | 100 | 323.333 | 300 | 300 | pass |
| charts | table | `task_charts__table__absolute_difference_between_rows_over_year_interval` | ['bbox_map'] | 100 | 200 | 281.98 | 35.523 | 35.523 | pass |
| charts | table | `task_charts__table__categorical_value_count` | ['bbox_set'] | 100 | 613 | 97.32 | 36.761 | 36.761 | pass |
| charts | table | `task_charts__table__column_rank_label` | ['bbox'] | 100 | 100 | 116.064 | 36.762 | 36.762 | pass |
| charts | table | `task_charts__table__column_summary_value` | ['bbox'] | 100 | 100 | 116.208 | 700 | 116.208 | pass |
| charts | table | `task_charts__table__filtered_column_mean` | ['bbox_set_map'] | 100 | 1310 | 116.64 | 36.904 | 36.904 | pass |
| charts | table | `task_charts__table__interval_value_count` | ['bbox_set'] | 100 | 841 | 117.36 | 37.285 | 37.285 | pass |
| charts | table | `task_charts__table__sum_absolute_differences_between_rows_over_year_interval` | ['bbox_set'] | 100 | 890 | 70.495 | 35.428 | 35.428 | pass |
| charts | table | `task_charts__table__threshold_count` | ['bbox_set'] | 100 | 842 | 117.36 | 36.857 | 36.857 | pass |
| charts | treemap | `task_charts__treemap__group_total_value` | ['bbox_set'] | 100 | 501 | 119.1 | 34.159 | 34.159 | pass |
| charts | treemap | `task_charts__treemap__parent_total_extremum_label` | ['bbox_set'] | 100 | 502 | 96.021 | 34.973 | 34.973 | pass |
| charts | treemap | `task_charts__treemap__repeated_leaf_aggregate_value` | ['bbox_set'] | 100 | 488 | 108.136 | 32 | 32 | pass |
| charts | violin | `task_charts__violin__modality_label` | ['bbox'] | 100 | 100 | 49.09 | 92.878 | 49.09 | pass |
| charts | violin | `task_charts__violin__mode_extremum_label` | ['bbox'] | 100 | 100 | 49.308 | 56 | 49.308 | pass |
| charts | violin | `task_charts__violin__support_width_extremum_label` | ['bbox'] | 100 | 100 | 49.332 | 81.268 | 49.332 | pass |
| charts | waterfall | `task_charts__waterfall__remove_step_final_total` | ['bbox_map'] | 100 | 200 | 53.556 | 29.5 | 29.5 | pass |
| charts | waterfall | `task_charts__waterfall__reverse_step_final_total` | ['bbox_map'] | 100 | 200 | 53.556 | 29.5 | 29.5 | pass |
| charts | waterfall | `task_charts__waterfall__running_total_extremum_value` | ['bbox'] | 100 | 100 | 49.093 | 29.5 | 29.5 | pass |
| charts | waterfall | `task_charts__waterfall__running_total_value` | ['bbox_set'] | 100 | 762 | 49.093 | 29.5 | 29.5 | pass |
