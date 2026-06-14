# `task_charts__area__stacked_band_interval_sum_value`

## Contract
1. Domain: `charts`
2. Scene id: `area`
3. Source scene package: `charts/area`
4. Query id: `default`
5. Semantic query details are recorded in trace params.

## Implementation
1. Registered class: `trace.tasks.charts.area.stacked_band_interval_sum_value.ChartsAreaStackedBandIntervalSumValueTask`
2. Prompt lookup scene: `charts/area`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `default` | `numeric.aggregate_sum` | `integer_value` | `point_set` |
