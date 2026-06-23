# `task_charts__region_map__numeric_threshold_region_count`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation path: `trace/tasks/charts/region_map/numeric_threshold_region_count.py`
4. Supported `query_id`: `greater_than_numeric_threshold_region_count`, `less_than_numeric_threshold_region_count`
5. Public task id: `task_charts__region_map__numeric_threshold_region_count`

## Implementation
1. Registered class: `trace.tasks.charts.region_map.numeric_threshold_region_count.ChartsMapNumericThresholdRegionCountTask`
2. Prompt bundle: `prompts/charts/region_map/charts_region_map_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the counted or summed map-region boxes only; legend, title, and context text are not annotation targets.
4. Adjacent-region tasks annotate matching neighbors and exclude the highlighted reference region.

## Program Contract
- `count(filter(regions, compare(value, threshold, direction))); output=integer_count; annotation=bbox_set(matching_regions); scene=region_map; scope=numeric_threshold_region_count`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `greater_than_numeric_threshold_region_count` | `count(regions where value > threshold)` | `integer_count` | `bbox_set` |
| `less_than_numeric_threshold_region_count` | `count(regions where value < threshold)` | `integer_count` | `bbox_set` |
