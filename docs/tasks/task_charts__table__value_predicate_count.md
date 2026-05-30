# `task_charts__table__value_predicate_count`

## Contract
1. Domain: `charts`
2. Scene id: `table`
3. Source implementation domain/group: `charts/table_counting`
4. Query id: `categorical_value_count`, `in_interval`, `threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` over matching table cells.

## Implementation
1. Registered class: `trace.tasks.charts.table.counting.value_count.ChartsTableValuePredicateCountTask`
2. Prompt lookup domain/group: `charts/table_counting`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
