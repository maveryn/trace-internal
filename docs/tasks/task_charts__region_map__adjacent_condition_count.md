# `task_charts__region_map__adjacent_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: `adjacent_category_count`, `adjacent_numeric_threshold_count`, `adjacent_same_category_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapAdjacentConditionCountTask`
2. Prompt lookup domain/group: `charts/map`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
