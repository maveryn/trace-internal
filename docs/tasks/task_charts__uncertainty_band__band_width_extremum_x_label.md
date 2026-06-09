# `task_charts__uncertainty_band__band_width_extremum_x_label`

## Contract
1. Domain: `charts`
2. Scene id: `uncertainty_band`
3. Source implementation domain/group: `charts/uncertainty_band`
4. Query id: sampled from `narrowest_band_x_label`, `widest_band_x_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.uncertainty_band.band_query.ChartsUncertaintyBandWidthExtremumXLabelTask`
2. Prompt lookup domain/group: `charts/uncertainty_band`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation maps `upper_bound` and `lower_bound` to pixel points on the target series band at the answer x-axis label.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `narrowest_band_x_label` | `argmin_x(width(vertical_interval(target_series_band_at_x)))` | `string_label` | `keyed_point_map` |
| `widest_band_x_label` | `argmax_x(width(vertical_interval(target_series_band_at_x)))` | `string_label` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
