# `task_charts__dashboard__category_panel_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `dashboard`
3. Source implementation domain/group: `charts/dashboard`
4. Query id: sampled from `category_panel_greater_than_threshold_count`, `category_panel_less_than_threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dashboard.category_panel_condition_count.ChartsDashboardCategoryPanelConditionCountTask`
2. Prompt lookup domain/group: `charts/dashboard`
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
| `category_panel_greater_than_threshold_count` | `count.group_predicate` | `integer_count` | `point_set` |
| `category_panel_less_than_threshold_count` | `count.group_predicate` | `integer_count` | `point_set` |
