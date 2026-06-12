# `task_charts__hexbin_density__threshold_bin_count`

## Contract
1. Domain: `charts`
2. Scene id: `hexbin_density`
3. Source implementation scene package: `charts/hexbin_density`
4. Query ids: `above_threshold_bin_count`, `below_threshold_bin_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.hexbin_density.threshold_bin_count.ChartsHexbinDensityThresholdBinCountTask`
2. Prompt lookup domain/scene: `charts/hexbin_density`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark every visible hex bin matching the discrete density-level threshold.
4. Renderer context such as axes, legends, titles, and background treatments is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `above_threshold_bin_count` | `count.hexbin_density_threshold` | `integer_count` | `bbox_set` |
| `below_threshold_bin_count` | `count.hexbin_density_threshold` | `integer_count` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
