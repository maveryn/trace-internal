# `task_charts__table__absolute_difference_between_rows_over_year_interval`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/absolute_difference_between_rows_over_year_interval.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `single`

## Program Contract

- Program schema: `abs(sum(values(row_a, years)) - sum(values(row_b, years))); output=integer_value; annotation=bbox_set(two_row_interval_cells); scene=table; scope=absolute_difference_between_rows_over_year_interval`.
- Program: absolute difference between two row sums over the same year interval.
- Answer: `integer`.
- Annotation schema: `bbox_set` over the two queried rows across the year interval.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
