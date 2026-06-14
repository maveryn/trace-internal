# `task_charts__errorbar_series__same_x_interval_overlap_count`

## Contract
1. Domain: `charts`
2. Scene id: `errorbar_series`
3. Source implementation domain/group: `charts/errorbar_series`
4. Query id: `single`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.errorbar_series.same_x_interval_overlap_count.ChartsErrorbarSeriesSameXIntervalOverlapCountTask`
2. Prompt lookup domain/group: `charts/errorbar_series`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `keyed_bbox_map`.
3. Annotation maps `target_errorbar` to the target error-bar box and each counted series label to its overlapping error-bar box at the same x-axis label.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(filter(series != target_series, overlaps(interval(errorbar(series,target_x)), interval(errorbar(target_series,target_x))))); output=integer_count; annotation=keyed_bbox_map(target_errorbar,matching_errorbar_marks_by_series); scene=errorbar_series; scope=same_x_interval_overlap_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count(series where series != target_series and overlaps(interval(errorbar(series, target_x)), interval(errorbar(target_series, target_x))))` | `integer_count` | `keyed_bbox_map` |
