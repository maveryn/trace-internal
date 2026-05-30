# `task_charts__table__column_rank_label`

## Contract
1. Domain: `charts`
2. Scene id: `table`
3. Source implementation domain/group: `charts/table_ranking`
4. Query id: `kth_rank_in_column`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` containing the queried-column region.

## Implementation
1. Registered class: `trace.tasks.charts.table.ranking.label.ChartsTableKthRankInColumnLabelTask`
2. Prompt lookup domain/group: `charts/table_ranking`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
