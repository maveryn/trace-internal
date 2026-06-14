# `task_charts__sunburst__parent_total_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `sunburst`
3. Source implementation domain/group: `charts/composition`
4. Query id: sampled from `highest_parent_total_label`, `lowest_parent_total_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.sunburst_hierarchy.ChartsCompositionSunburstParentTotalExtremumLabelTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest_parent_total_label` | `selection.extreme_metric_label` | `string_label` | `bbox_set` |
| `lowest_parent_total_label` | `selection.extreme_metric_label` | `string_label` | `bbox_set` |
