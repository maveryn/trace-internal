# `task_charts__combo_mark__directional_gap_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/scene: `charts/combo_mark`
4. Query id: `directional_gap_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.combo_mark.directional_gap_extremum_label.ChartsComboDirectionalGapExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/combo_mark`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation uses fixed keys `primary_mark` and `line_mark` for the answer category; dynamic category-label keys are not used.
4. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
5. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `directional_gap_extremum_label` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
