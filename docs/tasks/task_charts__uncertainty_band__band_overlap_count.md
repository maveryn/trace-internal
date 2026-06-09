# `task_charts__uncertainty_band__band_overlap_count`

## Contract
1. Domain: `charts`
2. Scene id: `uncertainty_band`
3. Source implementation domain/group: `charts/uncertainty_band`
4. Query id: `band_overlap_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.uncertainty_band.band_query.ChartsUncertaintyBandOverlapCountTask`
2. Prompt lookup domain/group: `charts/uncertainty_band`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation marks one centered pixel point inside each counted band-overlap region at a visible x-axis label.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `band_overlap_count` | `count(x_label where intersects(vertical_interval(series_a_band_at_x), vertical_interval(series_b_band_at_x)))` | `integer_value` | `point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
