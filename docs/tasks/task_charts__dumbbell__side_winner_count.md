# `task_charts__dumbbell__side_winner_count`

## Contract
1. Domain: `charts`
2. Scene id: `dumbbell`
3. Source implementation domain/group: `charts/dumbbell`
4. Query ids: `series_a_greater_threshold_count`, `series_b_greater_threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dumbbell.side_winner_count.ChartsDumbbellSideWinnerCountTask`
2. Prompt lookup domain/group: `charts/dumbbell`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `series_a_greater_threshold_count` | `count.pairwise_comparison` | `integer_count` | `bbox_set` |
| `series_b_greater_threshold_count` | `count.pairwise_comparison` | `integer_count` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
