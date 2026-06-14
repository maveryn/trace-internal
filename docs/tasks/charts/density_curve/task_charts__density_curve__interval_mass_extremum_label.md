# `task_charts__density_curve__interval_mass_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `density_curve`
3. Source implementation domain/scene: `charts/density_curve`
4. Query ids: `greatest_interval_mass_label`, `least_interval_mass_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.density_curve.interval_mass_extremum_label.ChartsDistributionDensityCurveIntervalMassExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/density_curve`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the shaded area under the answer curve inside the marked interval, not the legend label, title, or interval label.
4. Renderer context such as legends, axes, interval guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `greatest_interval_mass_label` | `selection.density_interval_mass_extremum_label` | `string_label` | `keyed_bbox_map` |
| `least_interval_mass_label` | `selection.density_interval_mass_extremum_label` | `string_label` | `keyed_bbox_map` |
