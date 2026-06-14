# `task_charts__density_curve__mode_location_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `density_curve`
3. Source implementation domain/scene: `charts/density_curve`
4. Query ids: `leftmost_mode_label`, `rightmost_mode_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.density_curve.mode_location_extremum_label.ChartsDistributionDensityCurveModeLocationExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/density_curve`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the visible dominant-peak marker for the answer curve, not the legend label, title, or axis text.
4. Renderer context such as legends, axes, interval guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `leftmost_mode_label` | `selection.density_mode_location_extremum_label` | `string_label` | `keyed_bbox_map` |
| `rightmost_mode_label` | `selection.density_mode_location_extremum_label` | `string_label` | `keyed_bbox_map` |
