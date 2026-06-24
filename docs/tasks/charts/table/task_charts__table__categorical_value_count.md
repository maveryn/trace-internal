# `task_charts__table__categorical_value_count`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/categorical_value_count.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `single`

## Program Contract

- Program schema: `count(row where category(column) == target_category); output=integer_count; annotation=bbox_set(matching_category_cells); scene=table; scope=categorical_value_count`.
- Program: count(row where category(column) equals target category).
- Answer: `integer`.
- Annotation schema: `bbox_set` over every matching category cell.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
