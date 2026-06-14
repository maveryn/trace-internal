# `task_charts__curve_panels__panel_curve_threshold_crossing_count`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/curve_panels`
4. Query ids: `panel_curve_upward_threshold_crossing_count`, `panel_curve_downward_threshold_crossing_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.curve_panels.panel_curve_threshold_crossing_count.ChartsScientificPanelCurveThresholdCrossingCountTask`
2. Prompt lookup domain/group: `charts/curve_panels`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `panel_curve_upward_threshold_crossing_count` | `count.intersection_or_crossing` | `integer_count` | `point_set` |
| `panel_curve_downward_threshold_crossing_count` | `count.intersection_or_crossing` | `integer_count` | `point_set` |
