# `task_charts__table__threshold_count`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/threshold_count.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `above_threshold_count`, `below_threshold_count`

## Program Contract

- Program schema: `count(row where value(column) threshold_compare threshold); output=integer_count; annotation=bbox_set(matching_cells); scene=table; scope=threshold_count`.
- Program: count(row where value(column) is above/below threshold).
- Answer: `integer`.
- Annotation schema: `bbox_set` over every matching value cell.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
