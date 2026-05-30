# `task_charts__table__column_summary_value`

## Contract
1. Domain: `charts`
2. Scene id: `table`
3. Source implementation domain/group: `charts/table_statistics`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` over the queried column or the selected filter/target cells.

## Implementation
1. Registered class: `trace.tasks.charts.table.statistics.column_summary_value.ChartsTableColumnSummaryValueTask`
2. Prompt lookup domain/group: `charts/table_statistics`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
