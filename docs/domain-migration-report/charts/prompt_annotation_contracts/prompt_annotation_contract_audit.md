# Prompt/Annotation Contract Audit

- tasks: `180`
- expected public-facing query ids: `340`
- sampled query ids: `340`
- sampled instances: `340`
- issues: `85`
- issue categories: `{'annotation_prompt': 85}`
- report directory: `docs/domain-migration-report/charts/prompt_annotation_contracts`

Artifacts:
- Prompt redundancy: `docs/domain-migration-report/charts/prompt_annotation_contracts/prompt_redundancy_audit.md`
- Annotation prompt clarity: `docs/domain-migration-report/charts/prompt_annotation_contracts/annotation_prompt_audit.md`
- Annotation projection validation: `docs/domain-migration-report/charts/prompt_annotation_contracts/annotation_projection_validation.md`
- Annotation overlay samples: `docs/domain-migration-report/charts/prompt_annotation_contracts/annotation_overlay_samples`
- Machine-readable report: `docs/domain-migration-report/charts/prompt_annotation_contracts/prompt_annotation_audit.json`

## Domain Task Counts

| domain | tasks |
| --- | ---: |
| charts | 180 |

## Highest Priority Issues

| severity | category | code | task | variant | mode | message |
| --- | --- | --- | --- | --- | --- | --- |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__bar_3d__category_extremum_gap_value | single | answer_and_annotation | point_map prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__bar_3d__category_total_gap_value | single | answer_and_annotation | point_set_map prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__bar_3d__pairwise_comparison_count | single | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__bar_3d__pairwise_comparison_count | single | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__bar_3d__series_total_gap_value | single | answer_and_annotation | point_set_map prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__candlestick__range_extremum_label | largest_body_range_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__candlestick__range_extremum_label | largest_body_range_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__candlestick__range_extremum_label | largest_wick_range_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__candlestick__range_extremum_label | largest_wick_range_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__candlestick__range_extremum_label | smallest_body_range_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__candlestick__range_extremum_label | smallest_body_range_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__candlestick__range_extremum_label | smallest_wick_range_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__candlestick__range_extremum_label | smallest_wick_range_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__combo_mark__dual_threshold_condition_count | primary_above_and_line_above | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__combo_mark__dual_threshold_condition_count | primary_above_and_line_above | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__combo_mark__dual_threshold_condition_count | primary_above_and_line_below | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__combo_mark__dual_threshold_condition_count | primary_above_and_line_below | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__combo_mark__dual_threshold_condition_count | primary_below_and_line_above | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__combo_mark__dual_threshold_condition_count | primary_below_and_line_above | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__combo_mark__interval_threshold_condition_count | line_between_and_primary_above | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__combo_mark__interval_threshold_condition_count | line_between_and_primary_above | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__combo_mark__interval_threshold_condition_count | primary_between_and_line_above | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__combo_mark__interval_threshold_condition_count | primary_between_and_line_above | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__absolute_gap_threshold_count | absolute_gap_at_least_threshold_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__absolute_gap_threshold_count | absolute_gap_at_least_threshold_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__absolute_gap_threshold_count | absolute_gap_at_most_threshold_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__absolute_gap_threshold_count | absolute_gap_at_most_threshold_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__gap_rank_row_label | largest_gap_rank_row_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__gap_rank_row_label | largest_gap_rank_row_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__gap_rank_row_label | smallest_gap_rank_row_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__gap_rank_row_label | smallest_gap_rank_row_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__side_winner_count | series_a_greater_threshold_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__side_winner_count | series_a_greater_threshold_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__dumbbell__side_winner_count | series_b_greater_threshold_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__dumbbell__side_winner_count | series_b_greater_threshold_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__interval_width_rank_label | narrowest_interval_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__interval_width_rank_label | narrowest_interval_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__interval_width_rank_label | second_narrowest_interval_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__interval_width_rank_label | second_narrowest_interval_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__interval_width_rank_label | second_widest_interval_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__interval_width_rank_label | second_widest_interval_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__interval_width_rank_label | widest_interval_label | answer_and_annotation | segment prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__interval_width_rank_label | widest_interval_label | answer_and_annotation | segment prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__reference_containment_count | single | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__reference_containment_count | single | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__reference_exclusion_side_count | entirely_above_reference_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__reference_exclusion_side_count | entirely_above_reference_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__error_interval__reference_exclusion_side_count | entirely_below_reference_count | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |
| warning | annotation_prompt | missing_pixel_space_wording | task_charts__error_interval__reference_exclusion_side_count | entirely_below_reference_count | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_point_notation | task_charts__errorbar_series__same_x_interval_overlap_count | single | answer_and_annotation | segment_set prompt should explicitly use [x, y] pixel points. |

_Showing first 50 of 85 issues._
