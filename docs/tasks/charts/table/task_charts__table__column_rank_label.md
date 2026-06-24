# `task_charts__table__column_rank_label`

## Public Contract

1. Domain: `charts`
2. Scene: `table`
3. Source file: `trace/tasks/charts/table/column_rank_label.py`
4. Prompt assets: `prompts/charts/table/*_v1.json`
5. Query ids: `highest_rank_in_column`, `lowest_rank_in_column`

## Program Contract

- Program schema: `rank(rows by value(column), direction, rank_k); output=row_label; annotation=bbox(answer_value_cell); scene=table; scope=column_rank_label`.
- Program: rank rows by one column and return the row label at the sampled rank.
- Answer: `string` row label.
- Annotation schema: `bbox` for the answer row cell in the queried column.
- The answer and annotation are bound from the same sampled table execution trace.

## Review Notes

This task uses the scene-package layout. Scene-local reusable code lives under `trace/tasks/charts/table/shared/`; public task files own objective logic, query selection, answer binding, and annotation binding.
