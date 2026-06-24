# `task_charts__table__column_summary_value`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/column_summary_value.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `column_sum`, `column_mean`, `column_median`

## Program Contract

- Program schema: `aggregate(values(column), operation=sum|mean|median); output=integer_value; annotation=bbox(column_values); scene=table; scope=column_summary_value`.
- Program: aggregate all values in one numeric column using sum, mean, or median.
- Answer: `integer`.
- Annotation schema: `bbox` around the queried column value region.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
