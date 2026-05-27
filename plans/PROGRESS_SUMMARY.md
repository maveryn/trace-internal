# Calibration Progress Summary

This file is the task-level current-best index for the manual TRACE difficulty calibration pass.

Active task audit: `plans/active_task_audit.md`.
Current calibration plan and acceptance gates: `plans/CALIBRATION_PLAN.md`.

The current calibration artifact baseline is `v0`. All previous review and solve-rate artifacts were cleared from the active artifact roots; every task below is pending fresh v0 review/calibration unless later updated with regenerated baseline-tagged artifacts.

Only record numbers here when they were obtained with the current code/config and generated artifacts that declare `calibration_baseline: "v0"`, or with an explicit config override documented in the task record. Do not copy measurements from non-current model gates, sample counts, or artifact layouts into this file.

The current standard is intentionally not duplicated here; use `plans/CALIBRATION_PLAN.md` so there is only one active calibration policy.

Column guide:

- `Best status`: `pending_v0_review`, `reviewed_pending_probe`, `distribution_failed`, `probed`, `needs_manual_tuning`, `partial`, `accepted`, `removed`, `blocked`, or `dropped`.
- `Best config`: short label for the retained current-code/current-config support.
- `Hard/Easy/Band`: fractions from the retained current calibration artifact.
- `Artifacts`: exact parquet, review workbook, and model-output references when available.

## Charts

charts has 100 active public task ids across 33 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_charts__area__interval_area_value` | pending_v0_review | current public task; scene `area` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__area__stacked_band_dominance_label` | pending_v0_review | current public task; scene `area` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__area__stacked_band_interval_sum_value` | pending_v0_review | current public task; scene `area` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__bar_3d__axis_gap_value` | pending_v0_review | current public task; scene `bar_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__bar_3d__axis_total_value` | pending_v0_review | current public task; scene `bar_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__bar_3d__condition_count` | pending_v0_review | current public task; scene `bar_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__boxplot__median_rank_difference_value` | pending_v0_review | current public task; scene `boxplot` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__boxplot__paired_median_shift_label` | pending_v0_review | current public task; scene `boxplot` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__boxplot__summary_statistic_label` | pending_v0_review | current public task; scene `boxplot` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__candlestick__counterfactual_close_value` | pending_v0_review | current public task; scene `candlestick` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__candlestick__range_extremum_label` | pending_v0_review | current public task; scene `candlestick` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__combo_mark__conditioned_extremum_label` | pending_v0_review | current public task; scene `combo_mark` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__combo_mark__cross_mark_difference_value` | pending_v0_review | current public task; scene `combo_mark` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__combo_mark__dual_condition_count` | pending_v0_review | current public task; scene `combo_mark` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__combo_mark__gap_extremum_label` | pending_v0_review | current public task; scene `combo_mark` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__combo_mark__interval_change_comparison_value` | pending_v0_review | current public task; scene `combo_mark` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__curve_panels__cross_panel_delta_extremum_label` | pending_v0_review | current public task; scene `curve_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__curve_panels__curve_at_x_extremum_label` | pending_v0_review | current public task; scene `curve_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__curve_panels__curve_intersection_count` | pending_v0_review | current public task; scene `curve_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__curve_panels__earliest_maximum_panel_label` | pending_v0_review | current public task; scene `curve_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__curve_panels__threshold_series_count` | pending_v0_review | current public task; scene `curve_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dashboard__dual_condition_count` | pending_v0_review | current public task; scene `dashboard` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dashboard__dual_source_target_sum_value` | pending_v0_review | current public task; scene `dashboard` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dashboard__panel_gap_extremum_category_label` | pending_v0_review | current public task; scene `dashboard` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dashboard__source_rank_difference_value` | pending_v0_review | current public task; scene `dashboard` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dashboard__source_rank_target_value` | pending_v0_review | current public task; scene `dashboard` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dumbbell__gap_rank_row_label` | pending_v0_review | current public task; scene `dumbbell` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__dumbbell__pair_relation_count` | pending_v0_review | current public task; scene `dumbbell` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__error_interval__interval_width_rank_label` | pending_v0_review | current public task; scene `error_interval` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__error_interval__reference_relation_count` | pending_v0_review | current public task; scene `error_interval` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__heatmap__axis_cell_extremum_label` | pending_v0_review | current public task; scene `heatmap` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__heatmap__axis_condition_extremum_label` | pending_v0_review | current public task; scene `heatmap` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__heatmap__condition_run_extremum_label` | pending_v0_review | current public task; scene `heatmap` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__histogram__cumulative_rank_bin_label` | pending_v0_review | current public task; scene `histogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__histogram__interval_value` | pending_v0_review | current public task; scene `histogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__marker_map__marker_region_extremum_label` | pending_v0_review | current public task; scene `marker_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__marker_map__marker_region_threshold_count` | pending_v0_review | current public task; scene `marker_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__matrix__axis_extremum_label` | pending_v0_review | current public task; scene `matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__matrix__threshold_cell_count` | pending_v0_review | current public task; scene `matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__multiseries__category_total_extremum_label` | pending_v0_review | current public task; scene `multiseries` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__multiseries__ranked_metric_extremum_label` | pending_v0_review | current public task; scene `multiseries` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__multiseries__series_comparison_count` | pending_v0_review | current public task; scene `multiseries` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__parallel_coords__axis_condition_count` | pending_v0_review | current public task; scene `parallel_coords` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__parallel_coords__axis_delta_extremum_label` | pending_v0_review | current public task; scene `parallel_coords` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__parallel_coords__crossing_count` | pending_v0_review | current public task; scene `parallel_coords` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__part_whole__adjacent_transfer_gap_value` | pending_v0_review | current public task; scene `part_whole` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__part_whole__order_count_conversion_value` | pending_v0_review | current public task; scene `part_whole` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__part_whole__order_sector_angle_value` | pending_v0_review | current public task; scene `part_whole` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__part_whole__order_share_sum_value` | pending_v0_review | current public task; scene `part_whole` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__pictogram__category_total_value` | pending_v0_review | current public task; scene `pictogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__pictogram__group_difference_value` | pending_v0_review | current public task; scene `pictogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__pictogram__threshold_count` | pending_v0_review | current public task; scene `pictogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radar__profile_advantage_count` | pending_v0_review | current public task; scene `radar` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radar__threshold_metric_count_for_panel` | pending_v0_review | current public task; scene `radar` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radar__threshold_panel_count` | pending_v0_review | current public task; scene `radar` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radial_progress__condition_count` | pending_v0_review | current public task; scene `radial_progress` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radial_sankey__dominant_endpoint_label` | pending_v0_review | current public task; scene `radial_sankey` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__radial_sankey__transfer_total_value` | pending_v0_review | current public task; scene `radial_sankey` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__region_map__adjacent_condition_count` | pending_v0_review | current public task; scene `region_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__region_map__border_neighbor_count` | pending_v0_review | current public task; scene `region_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__region_map__continent_filtered_count` | pending_v0_review | current public task; scene `region_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__region_map__region_category_count` | pending_v0_review | current public task; scene `region_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__region_map__region_value_count` | pending_v0_review | current public task; scene `region_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__sankey__node_side_total_value` | pending_v0_review | current public task; scene `sankey` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__sankey__path_value` | pending_v0_review | current public task; scene `sankey` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__scatter_cluster__cluster_feature_extremum_label` | pending_v0_review | current public task; scene `scatter_cluster` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__scatter_cluster__cluster_trend_direction_label` | pending_v0_review | current public task; scene `scatter_cluster` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__scatter_readout__series_point_lookup_value` | pending_v0_review | current public task; scene `scatter_readout` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__scatter_readout__series_x_extremum_label` | pending_v0_review | current public task; scene `scatter_readout` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__counterfactual_value` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__interval_change_value` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__monotone_streak_length` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__order_statistic_label` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__order_statistic_value` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__threshold_crossing_label` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__turning_point_count` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__single_series__value_predicate_count` | pending_v0_review | current public task; scene `single_series` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__size_encoding__category_total_extremum_label` | pending_v0_review | current public task; scene `size_encoding` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__size_encoding__filtered_item_extremum_label` | pending_v0_review | current public task; scene `size_encoding` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__size_encoding__reference_size_neighbor_label` | pending_v0_review | current public task; scene `size_encoding` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__small_multiple__aggregate_value` | pending_v0_review | current public task; scene `small_multiple` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__small_multiple__difference_value` | pending_v0_review | current public task; scene `small_multiple` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__sunburst__conditional_leaf_count` | pending_v0_review | current public task; scene `sunburst` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__sunburst__parent_total_extremum_label` | pending_v0_review | current public task; scene `sunburst` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__sunburst__parent_total_value` | pending_v0_review | current public task; scene `sunburst` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__surface_3d__panel_variation_label` | pending_v0_review | current public task; scene `surface_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__surface_3d__reference_nearest_label` | pending_v0_review | current public task; scene `surface_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__surface_3d__series_trend_label` | pending_v0_review | current public task; scene `surface_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__surface_3d__surface_extremum_label` | pending_v0_review | current public task; scene `surface_3d` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__table__column_rank_label` | pending_v0_review | current public task; scene `table` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__table__column_summary_value` | pending_v0_review | current public task; scene `table` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__table__temporal_row_interval_difference_value` | pending_v0_review | current public task; scene `table` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__table__value_predicate_count` | pending_v0_review | current public task; scene `table` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__treemap__group_total_value` | pending_v0_review | current public task; scene `treemap` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__treemap__repeated_leaf_aggregate_value` | pending_v0_review | current public task; scene `treemap` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__violin__feature_extremum_label` | pending_v0_review | current public task; scene `violin` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__violin__shape_feature_label` | pending_v0_review | current public task; scene `violin` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__waterfall__counterfactual_final_value` | pending_v0_review | current public task; scene `waterfall` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__waterfall__running_total_value` | pending_v0_review | current public task; scene `waterfall` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_charts__waterfall__threshold_crossing_label` | pending_v0_review | current public task; scene `waterfall` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Games

games has 80 active public task ids across 36 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_games__2048__best_move_label` | pending_v0_review | current public task; scene `2048` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__2048__move_result_value` | pending_v0_review | current public task; scene `2048` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__backgammon__destination_count` | pending_v0_review | current public task; scene `backgammon` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__battleship__ship_status_count` | pending_v0_review | current public task; scene `battleship` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bingo__completed_line_count` | pending_v0_review | current public task; scene `bingo` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bingo__line_sum_extremum_value` | pending_v0_review | current public task; scene `bingo` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bowling__first_pin_hit_label` | pending_v0_review | current public task; scene `bowling` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bowling__spare_path_label` | pending_v0_review | current public task; scene `bowling` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__brick_breaker__hit_row_remaining_count` | pending_v0_review | current public task; scene `brick_breaker` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__brick_breaker__trajectory_target_label` | pending_v0_review | current public task; scene `brick_breaker` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bubble_shooter__pop_color_label` | pending_v0_review | current public task; scene `bubble_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__bubble_shooter__shot_effect_count` | pending_v0_review | current public task; scene `bubble_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__blackjack_best_hand_label` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__exact_triple_count` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__longest_run_length` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__poker_best_hand_label` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__reference_condition_count` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__cards__trick_taking_winner_label` | pending_v0_review | current public task; scene `cards` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__checkers__max_capture_chain_length` | pending_v0_review | current public task; scene `checkers` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__checkers__move_count` | pending_v0_review | current public task; scene `checkers` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__chess__check_attacker_count` | pending_v0_review | current public task; scene `chess` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__chess__king_escape_square_count` | pending_v0_review | current public task; scene `chess` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__chess__marked_piece_destination_count` | pending_v0_review | current public task; scene `chess` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__chess__player_capture_piece_count` | pending_v0_review | current public task; scene `chess` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__chess_variant__marked_piece_destination_count` | pending_v0_review | current public task; scene `chess_variant` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__connect_four__move_count` | pending_v0_review | current public task; scene `connect_four` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__crossing__collision_time_value` | pending_v0_review | current public task; scene `crossing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__crossing__moving_object_count` | pending_v0_review | current public task; scene `crossing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__crossing__safe_route_label` | pending_v0_review | current public task; scene `crossing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__darts__condition_count` | pending_v0_review | current public task; scene `darts` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__darts__total_score_option_label` | pending_v0_review | current public task; scene `darts` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__dominoes__property_count` | pending_v0_review | current public task; scene `dominoes` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__dominoes__two_step_extension_label` | pending_v0_review | current public task; scene `dominoes` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__dots_and_boxes__capture_move_count` | pending_v0_review | current public task; scene `dots_and_boxes` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__dots_and_boxes__three_sided_box_count` | pending_v0_review | current public task; scene `dots_and_boxes` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__go__group_adjacent_enemy_count` | pending_v0_review | current public task; scene `go` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__go__group_liberty_count` | pending_v0_review | current public task; scene `go` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__hex__connection_gap_count` | pending_v0_review | current public task; scene `hex` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__hex__winning_move_cell_label` | pending_v0_review | current public task; scene `hex` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__marble_chain__shot_direction_label` | pending_v0_review | current public task; scene `marble_chain` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__marble_chain__shot_effect_value` | pending_v0_review | current public task; scene `marble_chain` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__match3__best_swap_label` | pending_v0_review | current public task; scene `match3` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__match3__swap_effect_value` | pending_v0_review | current public task; scene `match3` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minecraft__ore_block_count` | pending_v0_review | current public task; scene `minecraft` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minecraft__resource_route_cost_value` | pending_v0_review | current public task; scene `minecraft` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minecraft__tunnel_clearance_count` | pending_v0_review | current public task; scene `minecraft` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minesweeper__forced_cell_count` | pending_v0_review | current public task; scene `minesweeper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minesweeper__satisfied_clue_count` | pending_v0_review | current public task; scene `minesweeper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minigolf__first_obstacle_label` | pending_v0_review | current public task; scene `minigolf` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__minigolf__shot_path_label` | pending_v0_review | current public task; scene `minigolf` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__nine_mens_morris__pieces_in_mill_count` | pending_v0_review | current public task; scene `nine_mens_morris` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__pacman__next_item_label` | pending_v0_review | current public task; scene `pacman` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__pacman__route_pellet_count` | pending_v0_review | current public task; scene `pacman` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__platformer__collectible_count` | pending_v0_review | current public task; scene `platformer` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__platformer__jump_landing_label` | pending_v0_review | current public task; scene `platformer` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__pool__blocking_ball_count` | pending_v0_review | current public task; scene `pool` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__pool__pottable_ball_count` | pending_v0_review | current public task; scene `pool` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__reversi__legal_destination_count` | pending_v0_review | current public task; scene `reversi` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__reversi__marked_move_flip_count` | pending_v0_review | current public task; scene `reversi` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__rhythm__hit_window_count` | pending_v0_review | current public task; scene `rhythm` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__rhythm__lane_choice_value` | pending_v0_review | current public task; scene `rhythm` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__snake__path_outcome_option_label` | pending_v0_review | current public task; scene `snake` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__snake__safe_direction_count` | pending_v0_review | current public task; scene `snake` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__snakes_ladders__best_roll_value` | pending_v0_review | current public task; scene `snakes_ladders` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__snakes_ladders__move_outcome_value` | pending_v0_review | current public task; scene `snakes_ladders` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__solitaire__foundation_ready_count` | pending_v0_review | current public task; scene `solitaire` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__solitaire__move_legality_label` | pending_v0_review | current public task; scene `solitaire` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__solitaire__tableau_sequence_count` | pending_v0_review | current public task; scene `solitaire` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__space_shooter__clear_shot_count` | pending_v0_review | current public task; scene `space_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__space_shooter__highest_threat_label` | pending_v0_review | current public task; scene `space_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__space_shooter__projectile_intercept_count` | pending_v0_review | current public task; scene `space_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__space_shooter__safe_lane_count` | pending_v0_review | current public task; scene `space_shooter` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__sudoku__marked_cell_candidate_count` | pending_v0_review | current public task; scene `sudoku` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__sudoku__marked_cell_value` | pending_v0_review | current public task; scene `sudoku` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__sudoku__repeated_digit_count` | pending_v0_review | current public task; scene `sudoku` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__sudoku__unit_missing_digits_count` | pending_v0_review | current public task; scene `sudoku` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__tetris__drop_result_label` | pending_v0_review | current public task; scene `tetris` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__tetris__line_clear_count` | pending_v0_review | current public task; scene `tetris` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__ultimate_tictactoe__local_tactic_label` | pending_v0_review | current public task; scene `ultimate_tictactoe` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_games__ultimate_tictactoe__small_board_status_count` | pending_v0_review | current public task; scene `ultimate_tictactoe` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Geometry

geometry has 75 active public task ids across 23 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_geometry__angle_relations__algebraic_angle_value` | pending_v0_review | current public task; scene `angle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__angle_relations__angle_chain_value` | pending_v0_review | current public task; scene `angle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__area_partition__parallelogram_area_partition_total_area_value` | pending_v0_review | current public task; scene `area_partition` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__area_partition__triangle_area_partition_total_area_value` | pending_v0_review | current public task; scene `area_partition` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__diameter_perpendicular_chord_length_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__inscribed_angle_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__intersecting_chords_arc_measure_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__multi_step_angle_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__secant_secant_length_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__tangent_chord_angle_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__circle_theorem__tangent_secant_length_value` | pending_v0_review | current public task; scene `circle_theorem` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__composite_area_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__composite_perimeter_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__curvilinear_composite_area_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__curvilinear_composite_perimeter_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__curvilinear_missing_side_from_area_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__composite_shape__curvilinear_sector_angle_value` | pending_v0_review | current public task; scene `composite_shape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__concentric_chord__concentric_circle_chord_value` | pending_v0_review | current public task; scene `concentric_chord` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__cone_net__cone_sector_net_value` | pending_v0_review | current public task; scene `cone_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_panels__quadrilateral_shape_match_label` | pending_v0_review | current public task; scene `coordinate_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__collinear_point_count` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__locus_panel_match_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__locus_point_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__missing_endpoint_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__point_in_polygon_count` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__quadrilateral_completion_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__same_quadrant_point_count` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__section_point_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__segment_relation_count` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__coordinate_plane__transformed_point_label` | pending_v0_review | current public task; scene `coordinate_plane` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__cuboid_views__cuboid_projection_surface_area_value` | pending_v0_review | current public task; scene `cuboid_views` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__function_graph__average_rate_value` | pending_v0_review | current public task; scene `function_graph` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__function_graph__extremum_count` | pending_v0_review | current public task; scene `function_graph` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__function_graph__reference_line_crossing_count` | pending_v0_review | current public task; scene `function_graph` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__function_panels__intersection_property_label` | pending_v0_review | current public task; scene `function_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__function_panels__relation_property_label` | pending_v0_review | current public task; scene `function_panels` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__angle_extremum_label` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__angle_type_count` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__angle_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__area_extremum_label` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__circle_circumference_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__ellipse_area_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__length_extremum_label` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__line_slope_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__perimeter_extremum_label` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__polygon_area_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__polygon_convexity_count` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__polygon_perimeter_value` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__quadrilateral_type_count` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__shape_type_count` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__graph_paper__triangle_type_count` | pending_v0_review | current public task; scene `graph_paper` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__incircle_tangents__incircle_radius_from_area_value` | pending_v0_review | current public task; scene `incircle_tangents` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__incircle_tangents__incircle_tangent_perimeter_value` | pending_v0_review | current public task; scene `incircle_tangents` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__paper_fold__paper_fold_angle_value` | pending_v0_review | current public task; scene `paper_fold` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__pythagorean_dissection__pythagorean_square_area_value` | pending_v0_review | current public task; scene `pythagorean_dissection` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__sector__sector_angle_relation_value` | pending_v0_review | current public task; scene `sector` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__sector__sector_measure_value` | pending_v0_review | current public task; scene `sector` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__shape_gallery__shape_relation_count` | pending_v0_review | current public task; scene `shape_gallery` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__shape_gallery__transformation_match_label` | pending_v0_review | current public task; scene `shape_gallery` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_cross_section__solid_cross_section_area_value` | pending_v0_review | current public task; scene `solid_cross_section` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_formula__solid_formula_missing_dimension_value` | pending_v0_review | current public task; scene `solid_formula` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_revolution__revolution_cone_volume_value` | pending_v0_review | current public task; scene `solid_revolution` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_revolution__revolution_cylinder_volume_value` | pending_v0_review | current public task; scene `solid_revolution` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_revolution__revolution_double_cone_volume_value` | pending_v0_review | current public task; scene `solid_revolution` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__solid_revolution__revolution_frustum_volume_value` | pending_v0_review | current public task; scene `solid_revolution` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__tangent_packing__tangent_packing_length_value` | pending_v0_review | current public task; scene `tangent_packing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__tangent_packing__tangent_packing_shaded_area_value` | pending_v0_review | current public task; scene `tangent_packing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__trapezoid_extension__trapezoid_extension_area_value` | pending_v0_review | current public task; scene `trapezoid_extension` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__trapezoid_extension__trapezoid_extension_length_value` | pending_v0_review | current public task; scene `trapezoid_extension` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__angle_bisector_segment_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__centroid_median_segment_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__parallel_section_length_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__pythagorean_length_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__right_triangle_angle_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_geometry__triangle_relations__right_triangle_missing_side_value` | pending_v0_review | current public task; scene `triangle_relations` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Graph

graph has 39 active public task ids across 8 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_graph__adjacency__component_count` | pending_v0_review | current public task; scene `adjacency` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__adjacency__mst_weight` | pending_v0_review | current public task; scene `adjacency` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__adjacency__traversal_kth_label` | pending_v0_review | current public task; scene `adjacency` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__automaton__accepted_string_label` | pending_v0_review | current public task; scene `automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__automaton__state_after_input_label` | pending_v0_review | current public task; scene `automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__binary_tree__node_property_count` | pending_v0_review | current public task; scene `binary_tree` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__binary_tree__node_relation_label` | pending_v0_review | current public task; scene `binary_tree` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__binary_tree__traversal_kth_label` | pending_v0_review | current public task; scene `binary_tree` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__binary_tree__tree_operation_label` | pending_v0_review | current public task; scene `binary_tree` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__flow_network__max_flow_value` | pending_v0_review | current public task; scene `flow_network` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__flow_network__min_cut_edge_count` | pending_v0_review | current public task; scene `flow_network` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__graph_options__structure_match_label` | pending_v0_review | current public task; scene `graph_options` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__metro__exact_distance_station_count` | pending_v0_review | current public task; scene `metro` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__metro__shortest_path_length` | pending_v0_review | current public task; scene `metro` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__metro__station_membership_count` | pending_v0_review | current public task; scene `metro` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__metro__transfer_count` | pending_v0_review | current public task; scene `metro` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__articulation_point_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__bridge_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__common_neighbor_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__component_membership_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__cross_color_edge_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__degree_extremum_value` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__degree_predicate_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__edge_attribute_label` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__edge_color_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__edge_text_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__isolated_after_removal_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__longest_path_length` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__mst_weight` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__named_node_degree_value` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__node_color_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__reachable_node_count` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__shortest_path_length` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__topological_position_value` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__unique_cycle_size` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__node_link__unique_node_label` | pending_v0_review | current public task; scene `node_link` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__pipe_network__bridge_count` | pending_v0_review | current public task; scene `pipe_network` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__pipe_network__junction_path_count` | pending_v0_review | current public task; scene `pipe_network` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_graph__pipe_network__shortest_path_length` | pending_v0_review | current public task; scene `pipe_network` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Icons

icons has 28 active public task ids across 11 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_icons__icon_field__type_frequency_count` | pending_v0_review | current public task; scene `icon_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__mirror_grid__mirror_symmetry_count` | pending_v0_review | current public task; scene `mirror_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__mirror_grid__reflection_match_label` | pending_v0_review | current public task; scene `mirror_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__closer_to_reference_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__reference_distance_rank_label` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__region_shape_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__shape_attribute_boolean_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__shape_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__shape_counterfactual_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__shape_pair_difference_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__named_field__shape_pair_total_count` | pending_v0_review | current public task; scene `named_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__overlap_grid__occlusion_order_count` | pending_v0_review | current public task; scene `overlap_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__pair_grid__pair_attribute_rule_count` | pending_v0_review | current public task; scene `pair_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__pair_grid__pair_geometric_transform_count` | pending_v0_review | current public task; scene `pair_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__paired_canvas__original_attribute_label` | pending_v0_review | current public task; scene `paired_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__paired_canvas__panel_attribute_change_count` | pending_v0_review | current public task; scene `paired_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__paired_canvas__panel_difference_count` | pending_v0_review | current public task; scene `paired_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__paired_canvas__panel_exact_match_count` | pending_v0_review | current public task; scene `paired_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__paired_canvas__panel_movement_direction_count` | pending_v0_review | current public task; scene `paired_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__pattern_grid__color_pattern_violation_index` | pending_v0_review | current public task; scene `pattern_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__pattern_grid__size_pattern_violation_index` | pending_v0_review | current public task; scene `pattern_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__reference_canvas__anchor_position_count` | pending_v0_review | current public task; scene `reference_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__reference_canvas__attribute_match_count` | pending_v0_review | current public task; scene `reference_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__reference_canvas__size_relation_count` | pending_v0_review | current public task; scene `reference_canvas` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__sequence_strip__missing_count_value` | pending_v0_review | current public task; scene `sequence_strip` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__sequence_strip__rotation_sequence_violation_index` | pending_v0_review | current public task; scene `sequence_strip` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__two_anchor__between_anchors_count` | pending_v0_review | current public task; scene `two_anchor` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_icons__venn_field__venn_region_shape_count` | pending_v0_review | current public task; scene `venn_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Illustrations

illustrations has 24 active public task ids across 14 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_illustrations__construction_site__equipment_zone_count` | pending_v0_review | current public task; scene `construction_site` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__construction_site__material_stack_count` | pending_v0_review | current public task; scene `construction_site` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__construction_site__worker_attribute_count` | pending_v0_review | current public task; scene `construction_site` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__difference_pair__object_difference_count` | pending_v0_review | current public task; scene `difference_pair` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__environment__feature_relation_count` | pending_v0_review | current public task; scene `environment` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__environment__lit_window_count` | pending_v0_review | current public task; scene `environment` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__image_cutout_board__jigsaw_piece_order` | pending_v0_review | current public task; scene `image_cutout_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__image_cutout_board__rotated_tile_label` | pending_v0_review | current public task; scene `image_cutout_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__indoor_room__container_object_count` | pending_v0_review | current public task; scene `indoor_room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__indoor_room__furniture_side_count` | pending_v0_review | current public task; scene `indoor_room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__indoor_room__surface_object_count` | pending_v0_review | current public task; scene `indoor_room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__library__section_book_count` | pending_v0_review | current public task; scene `library` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__market__customer_at_shop_count` | pending_v0_review | current public task; scene `market` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__market__shop_attribute_count` | pending_v0_review | current public task; scene `market` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__missing_patch__missing_patch_label` | pending_v0_review | current public task; scene `missing_patch` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__object_field__named_object_side_count` | pending_v0_review | current public task; scene `object_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__object_field__object_type_count` | pending_v0_review | current public task; scene `object_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__object_field__visible_part_count` | pending_v0_review | current public task; scene `object_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__park_playground__person_count` | pending_v0_review | current public task; scene `park_playground` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__park_playground__playground_equipment_count` | pending_v0_review | current public task; scene `park_playground` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__scene_options__odd_scene_label` | pending_v0_review | current public task; scene `scene_options` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__single_object_figure__visible_part_count` | pending_v0_review | current public task; scene `single_object_figure` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__source_scene_edit__object_count_after_edit` | pending_v0_review | current public task; scene `source_scene_edit` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_illustrations__transit_terminal__entity_location_count` | pending_v0_review | current public task; scene `transit_terminal` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Pages

pages has 29 active public task ids across 17 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_pages__calendar__marked_day_class_count` | pending_v0_review | current public task; scene `calendar` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__calendar__weekday_occurrence_date` | pending_v0_review | current public task; scene `calendar` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__command_matrix__command_intent_target_label` | pending_v0_review | current public task; scene `command_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__concept_map__branch_item_count` | pending_v0_review | current public task; scene `concept_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__concept_map__filtered_node_count` | pending_v0_review | current public task; scene `concept_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__concept_map__ordered_child_label` | pending_v0_review | current public task; scene `concept_map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__control_board__filter_count` | pending_v0_review | current public task; scene `control_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__cycle__offset_stage_label` | pending_v0_review | current public task; scene `cycle` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__form_section__section_expression_value` | pending_v0_review | current public task; scene `form_section` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__hierarchy__tree_count` | pending_v0_review | current public task; scene `hierarchy` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__infographic__column_profile_comparison_value` | pending_v0_review | current public task; scene `infographic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__infographic__filtered_metric_total_value` | pending_v0_review | current public task; scene `infographic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__infographic__filtered_section_extremum_label` | pending_v0_review | current public task; scene `infographic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__infographic__metric_arithmetic_value` | pending_v0_review | current public task; scene `infographic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__infographic__section_ranked_total_label` | pending_v0_review | current public task; scene `infographic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__map__navigation_label` | pending_v0_review | current public task; scene `map` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__navigation_flow__navigation_path_target_label` | pending_v0_review | current public task; scene `navigation_flow` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__paired_forms__reconciliation_value` | pending_v0_review | current public task; scene `paired_forms` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__process_flow__actor_handoff_count` | pending_v0_review | current public task; scene `process_flow` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__process_flow__condition_path_endpoint_label` | pending_v0_review | current public task; scene `process_flow` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__process_flow__filtered_node_count` | pending_v0_review | current public task; scene `process_flow` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__schedule__longer_than_reference_count` | pending_v0_review | current public task; scene `schedule` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__schedule__maximum_non_overlapping_count` | pending_v0_review | current public task; scene `schedule` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__schedule__overlap_count` | pending_v0_review | current public task; scene `schedule` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__schema__field_role_count` | pending_v0_review | current public task; scene `schema` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__schema__relationship_count` | pending_v0_review | current public task; scene `schema` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__timeline__interval_membership_count` | pending_v0_review | current public task; scene `timeline` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__web_action__web_action_target_label` | pending_v0_review | current public task; scene `web_action` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_pages__workspace__professional_target_label` | pending_v0_review | current public task; scene `workspace` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Physics

physics has 20 active public task ids across 12 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_physics__collision__sticky_collision_direction_choice` | pending_v0_review | current public task; scene `collision` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__collision__sticky_collision_velocity_component_value` | pending_v0_review | current public task; scene `collision` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__electrostatic_field__field_direction_choice` | pending_v0_review | current public task; scene `electrostatic_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__electrostatic_field__potential_value` | pending_v0_review | current public task; scene `electrostatic_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__electrostatic_field__zero_field_point_label` | pending_v0_review | current public task; scene `electrostatic_field` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__hydraulic__hydraulic_missing_value` | pending_v0_review | current public task; scene `hydraulic` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__lever__missing_weight_balance_value` | pending_v0_review | current public task; scene `lever` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__lever__side_torque_value` | pending_v0_review | current public task; scene `lever` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__magnetic_force__force_direction_choice` | pending_v0_review | current public task; scene `magnetic_force` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__paired_resistor__missing_resistor_value` | pending_v0_review | current public task; scene `paired_resistor` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__pulley__pulley_mechanical_advantage` | pending_v0_review | current public task; scene `pulley` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__pv_diagram__pv_process_sign_choice` | pending_v0_review | current public task; scene `pv_diagram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__pv_diagram__pv_work_value` | pending_v0_review | current public task; scene `pv_diagram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__ray_optics__ray_bounce_count` | pending_v0_review | current public task; scene `ray_optics` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__ray_optics__ray_target_hit_count` | pending_v0_review | current public task; scene `ray_optics` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__resistor__total_resistance_value` | pending_v0_review | current public task; scene `resistor` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__spring__spring_extension_difference` | pending_v0_review | current public task; scene `spring` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__spring__spring_missing_value` | pending_v0_review | current public task; scene `spring` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__wave_interference__interference_point_choice` | pending_v0_review | current public task; scene `wave_interference` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_physics__wave_interference__path_difference_value` | pending_v0_review | current public task; scene `wave_interference` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Puzzles

puzzles has 77 active public task ids across 34 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_puzzles__agent_automaton__agent_cell_flip_count` | pending_v0_review | current public task; scene `agent_automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__agent_automaton__agent_final_pose_label` | pending_v0_review | current public task; scene `agent_automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__analog_clock__offset_readout` | pending_v0_review | current public task; scene `analog_clock` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__arithmetic_constraint__arithmetic_constraint_value` | pending_v0_review | current public task; scene `arithmetic_constraint` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__arithmetic_constraint__cryptarithm_digit_value` | pending_v0_review | current public task; scene `arithmetic_constraint` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__arithmetic_constraint__number_wall_value` | pending_v0_review | current public task; scene `arithmetic_constraint` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__arithmetic_constraint__operator_grid_value` | pending_v0_review | current public task; scene `arithmetic_constraint` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cell_board__attribute_count` | pending_v0_review | current public task; scene `cell_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cell_board__color_region_count` | pending_v0_review | current public task; scene `cell_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cell_board__path_distance` | pending_v0_review | current public task; scene `cell_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cell_board__reachability_count` | pending_v0_review | current public task; scene `cell_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cell_board__symmetry_violation_count` | pending_v0_review | current public task; scene `cell_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__clock_collection__compare` | pending_v0_review | current public task; scene `clock_collection` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__color_gradient__color_gradient_completion_label` | pending_v0_review | current public task; scene `color_gradient` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__color_gradient__color_gradient_violation_cell_label` | pending_v0_review | current public task; scene `color_gradient` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__counterfactual_board__board_grid_count` | pending_v0_review | current public task; scene `counterfactual_board` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cube_net__cube_net_face_relation_label` | pending_v0_review | current public task; scene `cube_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cube_net__cube_rolling_result_label` | pending_v0_review | current public task; scene `cube_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__cyclic_order__cyclic_order_equivalent_label` | pending_v0_review | current public task; scene `cyclic_order` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__dice_probability__dice_conditional_event_value` | pending_v0_review | current public task; scene `dice_probability` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__dice_probability__dice_pair_event_value` | pending_v0_review | current public task; scene `dice_probability` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__dice_probability__dice_single_event_value` | pending_v0_review | current public task; scene `dice_probability` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__life_automaton__life_future_grid_label` | pending_v0_review | current public task; scene `life_automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__life_automaton__life_population_count` | pending_v0_review | current public task; scene `life_automaton` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__logic_grid__grid_king_non_touch_label` | pending_v0_review | current public task; scene `logic_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__logic_grid__grid_uniqueness_completion_label` | pending_v0_review | current public task; scene `logic_grid` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label` | pending_v0_review | current public task; scene `matchstick` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__matchstick__matchstick_number_transform_label` | pending_v0_review | current public task; scene `matchstick` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__maze__exit_reachability_label` | pending_v0_review | current public task; scene `maze` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__maze__reachable_exit_count` | pending_v0_review | current public task; scene `maze` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__bar_count_value` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__chord_harmony_label` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__dominant_chord_count` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__duration_equivalence_label` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__key_scale_label` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__meter_rhythm_label` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__music_staff__pitch_interval_label` | pending_v0_review | current public task; scene `music_staff` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__nonogram__nonogram_candidate_solution_label` | pending_v0_review | current public task; scene `nonogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__nonogram__nonogram_line_completion_label` | pending_v0_review | current public task; scene `nonogram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__overlay__overlay_result_label` | pending_v0_review | current public task; scene `overlay` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__paper_fold__paper_fold_result_label` | pending_v0_review | current public task; scene `paper_fold` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__paper_fold_cut__paper_fold_cut_result_label` | pending_v0_review | current public task; scene `paper_fold_cut` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__pipe_flow__pipe_flow_repair_tile_label` | pending_v0_review | current public task; scene `pipe_flow` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label` | pending_v0_review | current public task; scene `polyomino_missing` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__raven_matrix__raven_analogical_transform_label` | pending_v0_review | current public task; scene `raven_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__raven_matrix__raven_count_progression_label` | pending_v0_review | current public task; scene `raven_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__raven_matrix__raven_position_progression_label` | pending_v0_review | current public task; scene `raven_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__raven_matrix__raven_set_operation_label` | pending_v0_review | current public task; scene `raven_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__raven_matrix__raven_spatial_transform_label` | pending_v0_review | current public task; scene `raven_matrix` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__rubiks_net__rubiks_face_color_count_label` | pending_v0_review | current public task; scene `rubiks_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__rubiks_net__rubiks_move_result_label` | pending_v0_review | current public task; scene `rubiks_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__rubiks_net__rubiks_sticker_color_label` | pending_v0_review | current public task; scene `rubiks_net` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__sliding_block__sliding_block_blocker_count` | pending_v0_review | current public task; scene `sliding_block` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__sliding_block__sliding_block_move_result_label` | pending_v0_review | current public task; scene `sliding_block` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__sokoban__sokoban_box_target_relation_label` | pending_v0_review | current public task; scene `sokoban` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__sokoban__sokoban_path_sequence_label` | pending_v0_review | current public task; scene `sokoban` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__spinner_probability__spinner_compound_event_value` | pending_v0_review | current public task; scene `spinner_probability` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__spinner_probability__spinner_pair_event_value` | pending_v0_review | current public task; scene `spinner_probability` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__star_battle__star_battle_remaining_count` | pending_v0_review | current public task; scene `star_battle` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__star_battle__star_battle_valid_cell_label` | pending_v0_review | current public task; scene `star_battle` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__string_topology__string_component_count` | pending_v0_review | current public task; scene `string_topology` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__tangram__tangram_contact_count` | pending_v0_review | current public task; scene `tangram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__tangram__tangram_missing_piece_label` | pending_v0_review | current public task; scene `tangram` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__tents__tents_missing_tent_cell_label` | pending_v0_review | current public task; scene `tents` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__tents__tents_valid_candidate_count` | pending_v0_review | current public task; scene `tents` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__turing_tape__turing_written_symbol_count` | pending_v0_review | current public task; scene `turing_tape` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_count` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_painted_face_count` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_projection_consistency_label` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_projection_match_label` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_structure_change_count` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_cube__cube_visible_projection_count` | pending_v0_review | current public task; scene `voxel_cube` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_ladder__voxel_ladder_route_count` | pending_v0_review | current public task; scene `voxel_ladder` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__voxel_ladder__voxel_ladder_route_label` | pending_v0_review | current public task; scene `voxel_ladder` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__word_search__search_letter_count_value` | pending_v0_review | current public task; scene `word_search` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__word_search__search_location_label` | pending_v0_review | current public task; scene `word_search` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_puzzles__word_search__search_present_word_count` | pending_v0_review | current public task; scene `word_search` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |

## Three D

three_d has 15 active public task ids across 4 scenes. Fresh v0 review and solve-rate calibration are pending.

| Task | Best status | Best config | Hard | Easy | Band | Artifacts | Notes |
|---|---|---|---:|---:|---:|---|---|
| `task_three_d__object_scene__between_references_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__object_scene__camera_distance_extremum_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__object_scene__height_extremum_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__object_scene__object_relation_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__object_scene__occlusion_order_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__object_scene__reference_nearest_label` | pending_v0_review | current public task; scene `object_scene` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__room__wall_mounted_object_count` | pending_v0_review | current public task; scene `room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__room__wall_object_camera_distance_label` | pending_v0_review | current public task; scene `room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__room__wall_object_same_wall_reference_label` | pending_v0_review | current public task; scene `room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__room__wall_object_side_relation_label` | pending_v0_review | current public task; scene `room` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__street__intersection_nearest_label` | pending_v0_review | current public task; scene `street` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__street__lane_ahead_object_label` | pending_v0_review | current public task; scene `street` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__street__same_road_arm_reference_label` | pending_v0_review | current public task; scene `street` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__warehouse__robot_forward_path_label` | pending_v0_review | current public task; scene `warehouse` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
| `task_three_d__warehouse__robot_nearest_object_label` | pending_v0_review | current public task; scene `warehouse` | n/a | n/a | n/a |  | fresh v0 task review, distribution check, and solve-rate calibration pending |
