# `task_charts__boxplot__paired_median_shift_label`

## Contract
1. Domain: `charts`
2. Scene id: `boxplot`
3. Source implementation scene package: `charts/boxplot`
4. Query id: sampled from `paired_median_greatest_absolute_change_label`, `paired_median_greatest_decrease_label`, `paired_median_greatest_increase_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.boxplot.paired_median_shift_label.ChartsDistributionBoxplotPairedMedianShiftLabelTask`
2. Prompt lookup scene package: `charts/boxplot`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `paired_median_greatest_absolute_change_label` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
| `paired_median_greatest_decrease_label` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
| `paired_median_greatest_increase_label` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
