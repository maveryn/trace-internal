# `task_charts__dashboard__shared_label_rank_gap_extremum`

## Contract
1. Domain: `charts`
2. Scene id: `dashboard`
3. Source implementation domain/group: `charts/dashboard`
4. Query id: sampled from `high_to_low_largest_rank_gap_label`, `high_to_low_smallest_rank_gap_label`, `low_to_high_largest_rank_gap_label`, `low_to_high_smallest_rank_gap_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dashboard.shared_label_rank_gap_extremum.ChartsDashboardSharedLabelRankGapExtremumTask`
2. Prompt lookup domain/group: `charts/dashboard`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `high_to_low_largest_rank_gap_label` | `selection.rank_gap_extremum_label` | `string_label` | `keyed_point_map` |
| `high_to_low_smallest_rank_gap_label` | `selection.rank_gap_extremum_label` | `string_label` | `keyed_point_map` |
| `low_to_high_largest_rank_gap_label` | `selection.rank_gap_extremum_label` | `string_label` | `keyed_point_map` |
| `low_to_high_smallest_rank_gap_label` | `selection.rank_gap_extremum_label` | `string_label` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
