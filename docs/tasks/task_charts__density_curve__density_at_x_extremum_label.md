# `task_charts__density_curve__density_at_x_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `density_curve`
3. Source implementation domain/group: `charts/distribution`
4. Query ids: `highest_density_at_x_label`, `lowest_density_at_x_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.density_curve.ChartsDistributionDensityCurveDensityAtXExtremumLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the point where the answer curve intersects the marked x-value, not the legend label, title, axis text, or reference-line label.
4. Renderer context such as legends, axes, interval guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest_density_at_x_label` | `selection.density_at_x_extremum_label` | `string_label` | `keyed_point_map` |
| `lowest_density_at_x_label` | `selection.density_at_x_extremum_label` | `string_label` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
