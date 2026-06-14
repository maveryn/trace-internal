# `task_charts__curve_panels__endpoint_rank_panel_label`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/curve_panels`
4. Query ids: `start_highest_panel_label`, `start_lowest_panel_label`, `end_highest_panel_label`, `end_lowest_panel_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.curve_panels.endpoint_rank_panel_label.ChartsScientificEndpointRankPanelLabelTask`
2. Prompt lookup domain/group: `charts/curve_panels`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation should mark the selected endpoint marker in the answer subplot.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `start_highest_panel_label` | `selection.endpoint_rank_panel_label` | `string_label` | `point_set` |
| `start_lowest_panel_label` | `selection.endpoint_rank_panel_label` | `string_label` | `point_set` |
| `end_highest_panel_label` | `selection.endpoint_rank_panel_label` | `string_label` | `point_set` |
| `end_lowest_panel_label` | `selection.endpoint_rank_panel_label` | `string_label` | `point_set` |
