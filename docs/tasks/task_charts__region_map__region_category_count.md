# `task_charts__region_map__region_category_count`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: `categorical_region_count`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapRegionCategoryCountTask`
2. Prompt lookup domain/group: `charts/map`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
