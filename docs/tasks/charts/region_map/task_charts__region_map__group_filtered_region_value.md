# `task_charts__region_map__group_filtered_region_value`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation path: `trace/tasks/charts/region_map/group_filtered_region_value.py`
4. Supported `query_id`: `greater_than_group_filtered_region_value`, `less_than_group_filtered_region_value`
5. Public task id: `task_charts__region_map__group_filtered_region_value`

## Implementation
1. Registered class: `trace.tasks.charts.region_map.group_filtered_region_value.ChartsMapGroupFilteredRegionValueTask`
2. Prompt bundle: `prompts/charts/region_map/charts_region_map_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the counted or summed map-region boxes only; legend, title, and context text are not annotation targets.
4. Adjacent-region tasks annotate matching neighbors and exclude the highlighted reference region.

## Program Contract
- `sum(value(region) for region in filter(world_regions, continent == target_continent and compare(value, threshold, direction))); output=integer_value; annotation=bbox_set(included_world_regions); scene=region_map; scope=group_filtered_region_value`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `greater_than_group_filtered_region_value` | `sum(value(region) for world_regions where continent == target_continent and value > threshold)` | `integer_value` | `bbox_set` |
| `less_than_group_filtered_region_value` | `sum(value(region) for world_regions where continent == target_continent and value < threshold)` | `integer_value` | `bbox_set` |
