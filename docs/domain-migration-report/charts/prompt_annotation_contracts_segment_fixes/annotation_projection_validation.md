# Annotation Projection Validation

- sampled instances: `17`
- query ids covered: `17`
- annotation projection/geometry issues: `0`
- annotation types: `{'segment': 6, 'segment_set': 11}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_charts__bar_3d__pairwise_comparison_count | `single` | `{'single': 1}` | 2 | `` |
| task_charts__candlestick__range_extremum_label | `largest_body_range_label, largest_wick_range_label, smallest_body_range_label, smallest_wick_range_label` | `{'largest_body_range_label': 1, 'largest_wick_range_label': 1, 'smallest_body_range_label': 1, 'smallest_wick_range_label': 1}` | 4 | `` |
| task_charts__combo_mark__dual_threshold_condition_count | `primary_above_and_line_above, primary_above_and_line_below, primary_below_and_line_above` | `{'primary_above_and_line_above': 1, 'primary_above_and_line_below': 1, 'primary_below_and_line_above': 1}` | 3 | `` |
| task_charts__combo_mark__interval_threshold_condition_count | `line_between_and_primary_above, primary_between_and_line_above` | `{'line_between_and_primary_above': 1, 'primary_between_and_line_above': 1}` | 2 | `` |
| task_charts__dumbbell__absolute_gap_threshold_count | `absolute_gap_at_least_threshold_count, absolute_gap_at_most_threshold_count` | `{'absolute_gap_at_least_threshold_count': 1, 'absolute_gap_at_most_threshold_count': 1}` | 2 | `` |
| task_charts__dumbbell__gap_rank_row_label | `largest_gap_rank_row_label, smallest_gap_rank_row_label` | `{'largest_gap_rank_row_label': 1, 'smallest_gap_rank_row_label': 1}` | 2 | `` |
| task_charts__dumbbell__side_winner_count | `series_a_greater_threshold_count, series_b_greater_threshold_count` | `{'series_a_greater_threshold_count': 1, 'series_b_greater_threshold_count': 1}` | 2 | `` |
| task_charts__radar__profile_advantage_count | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
