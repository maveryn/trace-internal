# `task_charts__table__filtered_column_mean`

## Contract
1. Domain: `charts`
2. Scene id: `table`
3. Source implementation domain/group: `charts/table_statistics`
4. Query id: `filtered_column_mean`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.table.statistics.column_summary_value.ChartsTableFilteredColumnMeanTask`
2. Prompt lookup domain/group: `charts/table_statistics`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.
