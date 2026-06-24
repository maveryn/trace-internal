# `task_charts__table__filtered_column_mean`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/filtered_column_mean.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `above_threshold_filtered_mean`, `below_threshold_filtered_mean`, `interval_filtered_mean`

## Program Contract

- Program schema: `mean(value(target_column) for row where filter_column satisfies predicate); output=integer_value; annotation=bbox_set_map(filter_cells,target_cells); scene=table; scope=filtered_column_mean`.
- Program: filter rows by one column predicate, then mean the selected target-column values.
- Answer: `integer`.
- Annotation schema: `bbox_set_map` with `filter_cells` and `target_cells`.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
