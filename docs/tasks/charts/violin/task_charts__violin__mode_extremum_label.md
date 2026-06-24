# `task_charts__violin__mode_extremum_label`

## Public Contract

1. Domain: `charts`
2. Scene: `violin`
3. Source file: `trace/tasks/charts/violin/mode_extremum_label.py`
4. Prompt assets: `prompts/charts/violin/charts_violin_v1.json`
5. Supported sampled `query_id`: `highest_mode`, `lowest_mode`

## Program Contract

- Program schema: `arg_extreme(label, mode_location(distribution(label)), direction={highest,lowest}); output=string_label; annotation=bbox(selected_violin); scene=violin; scope=mode_extremum_label`.
- Program: select the visible violin plot whose main density peak occurs at the highest or lowest value.
- Answer: `string`.
- Annotation schema: `bbox`, one box around the selected violin plot.
- The answer and annotation are bound from the same sampled violin execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns extremum direction selection, answer binding, annotation binding, prompt branch selection, and task-specific trace fields; scene-local shared code only provides violin sampling, rendering, prompt, and annotation primitives.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest_mode` | `argmax(label, mode_location(distribution(label)))` | `string_label` | `bbox` |
| `lowest_mode` | `argmin(label, mode_location(distribution(label)))` | `string_label` | `bbox` |
