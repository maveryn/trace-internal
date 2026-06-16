# `task_charts__marker_map__marker_region_threshold_count`

## Contract
1. Domain: `charts`
2. Scene id: `marker_map`
3. Source implementation scene package: `charts/marker_map`
4. Query ids: `greater_than_marker_region_threshold_count`, `less_than_marker_region_threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.marker_map.marker_region_threshold_count.ChartsMarkerMapMarkerRegionThresholdCountTask`
2. Prompt lookup domain/scene: `charts/marker_map`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks one marker-bubble box for every visible map region whose marker value satisfies the requested threshold predicate.
4. Renderer context such as map outlines, legends, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(region where compare(marker_value(region), threshold_value, relation={greater_than,less_than})); output=integer_count; annotation=bbox_set(marker_bubble(matching_regions)); scene=marker_map; scope=marker_region_threshold_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `greater_than_marker_region_threshold_count` | `count.one_bound_threshold(relation=greater_than)` | `integer_count` | `bbox_set` |
| `less_than_marker_region_threshold_count` | `count.one_bound_threshold(relation=less_than)` | `integer_count` | `bbox_set` |
