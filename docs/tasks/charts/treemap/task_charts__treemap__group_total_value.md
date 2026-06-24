# `task_charts__treemap__group_total_value`

## Public Contract

1. Domain: `charts`
2. Scene: `treemap`
3. Source file: `trace/tasks/charts/treemap/group_total_value.py`
4. Prompt assets: `prompts/charts/treemap/charts_treemap_v1.json`
5. Supported sampled `query_id`: `single`

## Program Contract

- Program schema: `sum(value(child) for child in parent); output=integer_value; annotation=bbox_set(parent_child_value_boxes); scene=treemap; scope=group_total_value`.
- Program: sum every printed child value inside the requested parent category.
- Answer: `integer`.
- Annotation schema: `bbox_set` over the child value labels inside the selected parent rectangle.
- The answer and annotation are bound from the same sampled treemap execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns target parent selection, answer binding, annotation binding, and prompt slots; scene-local shared code only provides treemap data, rendering, prompt, and projection primitives.
