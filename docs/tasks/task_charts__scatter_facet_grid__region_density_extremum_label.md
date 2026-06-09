# `task_charts__scatter_facet_grid__region_density_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_facet_grid`
3. Source implementation domain/group: `charts/scatter`
4. Query ids: `upper_right_density_extremum_label`, `upper_left_density_extremum_label`, `lower_right_density_extremum_label`, `lower_left_density_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scatter.facet_grid_query.ChartsScatterFacetGridRegionDensityExtremumLabelTask`
2. Prompt lookup domain/group: `charts/scatter`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the densest supporting point region inside the answer panel's queried quadrant, not the panel title, axes, or surrounding context.
4. Renderer context such as axes, highlighted quadrant guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `upper_right_density_extremum_label` | `selection.local_density_extremum` | `string_label` | `keyed_bbox_map` |
| `upper_left_density_extremum_label` | `selection.local_density_extremum` | `string_label` | `keyed_bbox_map` |
| `lower_right_density_extremum_label` | `selection.local_density_extremum` | `string_label` | `keyed_bbox_map` |
| `lower_left_density_extremum_label` | `selection.local_density_extremum` | `string_label` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
