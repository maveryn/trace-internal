# `task_charts__contour_density__nearest_region_option_label`

## Contract
1. Domain: `charts`
2. Scene id: `contour_density`
3. Source implementation domain/group: `charts/contour_density`
4. Query id: `nearest_region_option_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.contour_density.field_query.ChartsContourDensityNearestRegionOptionLabelTask`
2. Prompt lookup domain/group: `charts/contour_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `option_letter`.
2. Annotation schema: `keyed_bbox_map`.
3. The rendered option regions use either `4` labels (`A..D`) or `6` labels (`A..F`) by construction.
4. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
5. Renderer context such as axes, decorative labels, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `nearest_region_option_label` | `select.nearest_reference_option_label` | `option_letter` | `keyed_bbox_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
