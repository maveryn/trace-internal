# `task_charts__region_map__named_region_set_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: `named_region_set_total_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapNamedRegionSetTotalValueTask`
2. Prompt lookup domain/group: `charts/map`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `named_region_set_total_value` | `numeric.aggregate_sum` | `integer_value` | `bbox_set` |
