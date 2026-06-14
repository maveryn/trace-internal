# `task_charts__error_interval__reference_exclusion_side_count`

## Contract
1. Domain: `charts`
2. Scene id: `error_interval`
3. Source implementation domain/group: `charts/error_interval`
4. Query ids: `entirely_above_reference_count`, `entirely_below_reference_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.error_interval.reference_exclusion_side_count.ChartsErrorIntervalReferenceExclusionSideCountTask`
2. Prompt lookup domain/group: `charts/error_interval`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(filter(intervals, interval_side(reference_value) == side)); output=integer_count; annotation=bbox_set(matching_interval_marks); scene=error_interval; scope=reference_exclusion_side_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `entirely_above_reference_count` | `count.reference_exclusion_side_count(side=above)` | `integer_count` | `bbox_set` |
| `entirely_below_reference_count` | `count.reference_exclusion_side_count(side=below)` | `integer_count` | `bbox_set` |
