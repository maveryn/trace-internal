# `task_charts__contour_density__reference_distance_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `contour_density`
3. Source implementation domain/group: `charts/contour_density`
4. Query id: `reference_distance_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.contour_density.field_query.ChartsContourDensityReferenceDistanceExtremumLabelTask`
2. Prompt lookup domain/group: `charts/contour_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as axes, decorative labels, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `reference_distance_extremum_label` | `select.reference_distance_extremum_label` | `string_label` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
