# `task_charts__table__interval_value_count`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/interval_value_count.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `single`

## Program Contract

- Program schema: `count(row where lower <= value(column) <= upper); output=integer_count; annotation=bbox_set(matching_cells); scene=table; scope=interval_value_count`.
- Program: count(row where lower <= value(column) <= upper).
- Answer: `integer`.
- Annotation schema: `bbox_set` over every value cell inside the inclusive interval.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
