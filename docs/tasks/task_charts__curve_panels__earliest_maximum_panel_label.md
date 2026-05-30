# `task_charts__curve_panels__earliest_maximum_panel_label`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `earliest_maximum_panel_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.multipanel_subplot_query.ChartsScientificEarliestMaximumPanelLabelTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence
1. Evidence type: `point_set`.
2. Points mark each compared subplot's maximum marker for the queried method.
