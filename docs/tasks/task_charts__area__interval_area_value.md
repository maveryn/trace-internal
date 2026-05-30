# `task_charts__area__interval_area_value`

## Contract
1. Domain: `charts`
2. Scene id: `area`
3. Source implementation domain/group: `charts/area`
4. Query id: `interval_area_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.area.panel_query.ChartsAreaIntervalAreaValueTask`
2. Prompt lookup domain/group: `charts/area`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence Contract
1. Answer schema: integer value.
2. Evidence schema: `point_set`.
3. Evidence marks the rendered point values from the queried start x-axis label through the queried end x-axis label.
4. Rendered area bands, interval shading, value-label bboxes, and chart axes are renderer metadata, not public evidence.
