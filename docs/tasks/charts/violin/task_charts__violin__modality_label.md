# `task_charts__violin__modality_label`

## Public Contract

1. Domain: `charts`
2. Scene: `violin`
3. Source file: `trace/tasks/charts/violin/modality_label.py`
4. Prompt assets: `prompts/charts/violin/charts_violin_v1.json`
5. Supported sampled `query_id`: `single`

## Program Contract

- Program schema: `select_unique(label where modality(distribution(label)) == bimodal); output=string_label; annotation=bbox(selected_violin); scene=violin; scope=modality_label`.
- Program: select the one visible violin plot with two clear density peaks.
- Answer: `string`.
- Annotation schema: `bbox`, one box around the selected violin plot.
- The answer and annotation are bound from the same sampled violin execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns the bimodal objective, answer binding, annotation binding, prompt branch selection, and task-specific trace fields; scene-local shared code only provides violin sampling, rendering, prompt, and annotation primitives.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `select_unique(label where modality(distribution(label)) == bimodal)` | `string_label` | `bbox` |
