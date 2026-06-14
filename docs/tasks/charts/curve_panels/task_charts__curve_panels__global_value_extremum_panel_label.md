# `task_charts__curve_panels__global_value_extremum_panel_label`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/curve_panels`
4. Query ids: `overall_maximum_value_panel_label`, `overall_minimum_value_panel_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.curve_panels.global_value_extremum_panel_label.ChartsScientificGlobalValueExtremumPanelLabelTask`
2. Prompt lookup domain/group: `charts/curve_panels`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation should mark the single global maximum/minimum marker that determines the answer.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `overall_maximum_value_panel_label` | `selection.global_extreme_point_panel_label` | `string_label` | `point_set` |
| `overall_minimum_value_panel_label` | `selection.global_extreme_point_panel_label` | `string_label` | `point_set` |
