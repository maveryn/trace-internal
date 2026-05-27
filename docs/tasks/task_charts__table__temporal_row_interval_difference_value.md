# `task_charts__table__temporal_row_interval_difference_value`

## Contract
1. Domain: `charts`
2. Scene id: `table`
3. Source implementation domain/group: `charts/table_temporal`
4. Query id: `absolute_difference_between_rows_over_year_interval`, `sum_absolute_differences_between_rows_over_year_interval`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.table.temporal.value.ChartsTableTemporalRowIntervalDifferenceValueTask`
2. Prompt lookup domain/group: `charts/table_temporal`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
