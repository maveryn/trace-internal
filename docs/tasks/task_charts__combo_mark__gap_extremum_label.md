# `task_charts__combo_mark__gap_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/group: `charts/combo`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `keyed_point_map`

## Implementation
1. Registered class: `trace.tasks.charts.combo.panel_query.ChartsComboGapExtremumLabelTask`
2. Prompt lookup domain/group: `charts/combo`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
5. Prompt-facing evidence binds only the answer category's two chart marks using keys of the form `<answer category>.primary` and `<answer category>.line`; axis labels and printed numeric labels remain visible annotations, not public evidence.
