# `task_charts__combo_mark__dual_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/group: `charts/combo`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_point_map`

## Implementation
1. Registered class: `trace.tasks.charts.combo.panel_query.ChartsComboDualConditionCountTask`
2. Prompt lookup domain/group: `charts/combo`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
5. Prompt-facing evidence binds each matching category's primary/line chart marks using keys of the form `<category>.primary` and `<category>.line`; category labels and printed numeric labels remain visible annotations, not public evidence.
