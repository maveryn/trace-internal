# `task_charts__combo_mark__interval_threshold_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/scene: `charts/combo_mark`
4. Query id: `interval_threshold_condition_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.combo_mark.interval_threshold_condition_count.ChartsComboIntervalThresholdConditionCountTask`
2. Prompt lookup domain/scene: `charts/combo_mark`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_pair_set`.
3. Annotation is one primary/line point pair for each matching category; each pair is ordered as `[primary mark point, line mark point]`.
4. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
5. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `interval_threshold_condition_count` | `count.interval_threshold_predicate` | `integer_count` | `point_pair_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
