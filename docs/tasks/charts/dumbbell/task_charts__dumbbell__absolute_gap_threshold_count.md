# `task_charts__dumbbell__absolute_gap_threshold_count`

## Contract
1. Domain: `charts`
2. Scene id: `dumbbell`
3. Source implementation domain/group: `charts/dumbbell`
4. Query ids: `absolute_gap_at_least_threshold_count`, `absolute_gap_at_most_threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dumbbell.absolute_gap_threshold_count.ChartsDumbbellAbsoluteGapThresholdCountTask`
2. Prompt lookup domain/group: `charts/dumbbell`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `segment_set`.
3. Annotation marks the two colored dot centers for each matching dumbbell row, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(row where compare(abs(value(series_a,row)-value(series_b,row)), threshold, relation={at_least,at_most})); output=integer_count; annotation=segment_set(matching_row_dot_centers); scene=dumbbell; scope=absolute_gap_threshold_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `absolute_gap_at_least_threshold_count` | `count.absolute_gap_threshold` | `integer_count` | `segment_set` |
| `absolute_gap_at_most_threshold_count` | `count.absolute_gap_threshold` | `integer_count` | `segment_set` |
