# `task_charts__marker_map__marker_region_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `marker_map`
3. Source implementation scene package: `charts/marker_map`
4. Query ids: `largest_marker_region_extremum_label`, `smallest_marker_region_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.marker_map.marker_region_extremum_label.ChartsMarkerMapMarkerRegionExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/marker_map`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox`.
3. Annotation marks the single marker-bubble box for the region whose visible label is the answer.
4. Renderer context such as map outlines, legends, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `select_label(arg_extreme(region, marker_value(region), direction={largest,smallest})); output=string_label; annotation=bbox(marker_bubble(selected_region)); scene=marker_map; scope=marker_region_extremum_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_marker_region_extremum_label` | `selection.extreme_metric_label(direction=largest)` | `string_label` | `bbox` |
| `smallest_marker_region_extremum_label` | `selection.extreme_metric_label(direction=smallest)` | `string_label` | `bbox` |
