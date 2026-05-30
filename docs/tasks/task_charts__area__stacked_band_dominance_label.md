# `task_charts__area__stacked_band_dominance_label`

## Contract
1. Domain: `charts`
2. Scene id: `area`
3. Source implementation domain/group: `charts/area`
4. Query id: `stacked_dominance_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.area.panel_query.ChartsAreaStackedDominanceLabelTask`
2. Prompt lookup domain/group: `charts/area`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence Contract
1. Answer schema: category label string.
2. Evidence schema: `point_set`.
3. Evidence marks all rendered category band-value points in the queried x-axis interval so the winning interval total can be checked.
4. Category colors, legend entries, value-label bboxes, and band polygons are renderer metadata, not public evidence.
