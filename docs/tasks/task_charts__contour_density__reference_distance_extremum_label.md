# `task_charts__contour_density__reference_distance_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `contour_density`
3. Source implementation scene package: `charts/contour_density`
4. Query ids: `point_nearest_region_label`, `point_farthest_region_label`, `vertical_line_nearest_region_label`, `vertical_line_farthest_region_label`, `horizontal_line_nearest_region_label`, `horizontal_line_farthest_region_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.contour_density.reference_distance_extremum_label.ChartsContourDensityReferenceDistanceExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/contour_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation should contain one bbox around the selected answer contour region.
4. Renderer context such as axes, decorative labels, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `point_nearest_region_label` | `select.reference_distance_extremum_label(reference=point, direction=nearest)` | `string_label` | `bbox_set` |
| `point_farthest_region_label` | `select.reference_distance_extremum_label(reference=point, direction=farthest)` | `string_label` | `bbox_set` |
| `vertical_line_nearest_region_label` | `select.reference_distance_extremum_label(reference=vertical_line, direction=nearest)` | `string_label` | `bbox_set` |
| `vertical_line_farthest_region_label` | `select.reference_distance_extremum_label(reference=vertical_line, direction=farthest)` | `string_label` | `bbox_set` |
| `horizontal_line_nearest_region_label` | `select.reference_distance_extremum_label(reference=horizontal_line, direction=nearest)` | `string_label` | `bbox_set` |
| `horizontal_line_farthest_region_label` | `select.reference_distance_extremum_label(reference=horizontal_line, direction=farthest)` | `string_label` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
