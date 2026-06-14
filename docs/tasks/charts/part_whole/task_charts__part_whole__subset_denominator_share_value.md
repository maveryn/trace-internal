# `task_charts__part_whole__subset_denominator_share_value`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Source implementation domain/group: `charts/composition`
4. Query id: `subset_denominator_share_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.share_arithmetic_value.ChartsCompositionSubsetDenominatorShareValueTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_map`.
3. Annotation maps every denominator-subset category label to an `[x,y]` point at the center of its chart segment.
4. Renderer context such as legends, table labels, decorative text, and titles is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `subset_denominator_share_value` | `round(100 * value(target_category) / sum(values(subset_categories)))` | `integer_value` | `keyed_point_map` |
