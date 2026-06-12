# `task_charts__contour_density__spread_extremum_region_label`

## Contract
1. Domain: `charts`
2. Scene id: `contour_density`
3. Source implementation scene package: `charts/contour_density`
4. Query id: `spread_extremum_region_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.contour_density.spread_extremum_region_label.ChartsContourDensitySpreadExtremumRegionLabelTask`
2. Prompt lookup domain/scene: `charts/contour_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the selected contour region as `answer_region`.
4. Renderer context such as axes, decorative labels, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `spread_extremum_region_label` | `select.visible_footprint_extremum_label` | `string_label` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
