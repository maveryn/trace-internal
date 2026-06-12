# `task_charts__contour_density__density_threshold_region_count`

## Contract
1. Domain: `charts`
2. Scene id: `contour_density`
3. Source implementation domain/group: `charts/contour_density`
4. Query id: `density_threshold_region_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.contour_density.field_query.ChartsContourDensityDensityThresholdRegionCountTask`
2. Prompt lookup domain/group: `charts/contour_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark every region matching the visible density-level threshold.
4. Renderer context such as axes, decorative labels, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `density_threshold_region_count` | `count.thresholded_visible_density_level` | `integer_count` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
