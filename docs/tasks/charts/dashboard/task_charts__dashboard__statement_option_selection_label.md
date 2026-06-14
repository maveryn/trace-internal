# `task_charts__dashboard__statement_option_selection_label`

## Contract
1. Domain: `charts`
2. Scene id: `dashboard`
3. Source implementation domain/group: `charts/dashboard`
4. Query id: `statement_option_selection_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.dashboard.statement_option_selection_label.ChartsDashboardStatementOptionSelectionLabelTask`
2. Prompt lookup domain/group: `charts/dashboard`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `option_letter`.
2. Annotation schema: `keyed_point_map`.
3. The rendered statement-option panel uses either `4` options (`A..D`) or `6` options (`A..F`) by construction.
4. Annotation should mark the two chart marks that verify the selected rendered statement option, not the option text itself.
5. Renderer context such as legends, axes, decorative labels, titles, distractor text, and statement-option text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `statement_option_selection_label` | `selection.statement_truth_option` | `option_letter` | `keyed_point_map` |
