# `task_charts__treemap__repeated_leaf_aggregate_value`

## Public Contract

1. Domain: `charts`
2. Scene: `treemap`
3. Source file: `trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py`
4. Prompt assets: `prompts/charts/treemap/charts_treemap_v1.json`
5. Supported `query_id` values: `treemap_repeated_leaf_sum_value`, `treemap_repeated_leaf_average_value`

## Program Contract

- Program schema: `aggregate(value(child_label across parents), operation=sum_or_average); output=integer_value; annotation=bbox_set(repeated_child_value_boxes); scene=treemap; scope=repeated_leaf_aggregate_value`.
- Program: find every occurrence of the requested child label across parent rectangles, then compute either the sum or the average of those printed values.
- Answer: `integer`.
- Annotation schema: `bbox_set` over every matching child value label across parent rectangles.
- The answer and annotation are bound from the same sampled treemap execution trace.

## Review Notes

This task uses the scene-package layout. Query ids select the aggregate operation; target child-label sampling remains objective-owned in the public task file and is recorded in trace params.
