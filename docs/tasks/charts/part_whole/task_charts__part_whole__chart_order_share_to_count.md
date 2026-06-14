# `task_charts__part_whole__chart_order_share_to_count`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Source implementation domain/group: `charts/composition`
4. Query id: `chart_order_share_to_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.share_arithmetic_value.ChartsCompositionChartOrderShareToCountTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `chart_order_share_to_count` | `numeric.derived_metric` | `integer_count` | `keyed_point_map` |
