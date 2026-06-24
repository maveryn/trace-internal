# `task_charts__violin__support_width_extremum_label`

## Public Contract

1. Domain: `charts`
2. Scene: `violin`
3. Source file: `trace/tasks/charts/violin/support_width_extremum_label.py`
4. Prompt assets: `prompts/charts/violin/charts_violin_v1.json`
5. Supported sampled `query_id`: `widest_support`, `narrowest_support`

## Program Contract

- Program schema: `arg_extreme(label, support_span(distribution(label)), direction={widest,narrowest}); output=string_label; annotation=bbox(selected_violin); scene=violin; scope=support_width_extremum_label`.
- Program: select the visible violin plot with the widest or narrowest vertical support span.
- Answer: `string`.
- Annotation schema: `bbox`, one box around the selected violin plot.
- The answer and annotation are bound from the same sampled violin execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns support-width direction selection, answer binding, annotation binding, prompt branch selection, and task-specific trace fields; scene-local shared code only provides violin sampling, rendering, prompt, and annotation primitives.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `widest_support` | `argmax(label, support_span(distribution(label)))` | `string_label` | `bbox` |
| `narrowest_support` | `argmin(label, support_span(distribution(label)))` | `string_label` | `bbox` |
