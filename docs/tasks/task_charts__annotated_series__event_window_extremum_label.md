# `task_charts__annotated_series__event_window_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `annotated_series`
3. Source implementation domain/group: `charts/annotated_series`
4. Query id: `event_window_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.annotated_series.event_window_query.ChartsAnnotatedSeriesEventWindowExtremumLabelTask`
2. Prompt lookup domain/group: `charts/annotated_series`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence Contract
1. Evidence type: `point_set`.
2. Prompt-facing evidence is the value-mark center for the selected extremum inside the highlighted window.
3. The highlighted-window box and annotation label box are retained in trace/render metadata as locators, not public evidence.
