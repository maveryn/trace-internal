# `task_charts__combo_mark__interval_threshold_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/scene: `charts/combo_mark`
4. Query ids: `primary_between_and_line_above`, `line_between_and_primary_above`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.combo_mark.interval_threshold_condition_count.ChartsComboIntervalThresholdConditionCountTask`
2. Prompt lookup domain/scene: `charts/combo_mark`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `segment_set`.
3. Annotation is a `segment_set`; each segment is `[[x1, y1], [x2, y2]]` and connects the primary-series mark point to the overlaid line mark point for one matching category.
4. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
5. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(x_label where in_interval(value(condition_series,x_label), lower_bound, upper_bound) and compare(value(target_series,x_label), threshold, relation=above)); output=integer_count; annotation=segment_set(matching_primary_line_marks); scene=combo_mark; scope=interval_threshold_condition_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `primary_between_and_line_above` | `count.interval_and_threshold_condition` | `integer_count` | `segment_set` |
| `line_between_and_primary_above` | `count.interval_and_threshold_condition` | `integer_count` | `segment_set` |
