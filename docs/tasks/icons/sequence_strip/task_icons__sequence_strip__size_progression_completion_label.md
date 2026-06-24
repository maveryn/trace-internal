# `task_icons__sequence_strip__size_progression_completion_label`

## Program Contract

`selection.sequence_completion(scene=sequence_strip, scope=four_cell_icon_sequence_with_visual_options, attribute=size, rule=constant_size_step, missing_role=question_mark_cell, output=option_label)`

## Identity

- Domain: `icons`
- Scene id: `sequence_strip`
- Task id: `task_icons__sequence_strip__size_progression_completion_label`
- Module: `trace/tasks/icons/sequence_strip/size_progression_completion_label.py`
- Prompt bundle: `icons_sequence_strip_v1`

## Contract

- Supported `query_id` values: `single`.
- Answer schema: `string`, one of `A`, `B`, `C`, or `D`.
- Annotation schema: scalar `bbox` around the correct bottom-row option box.
- The top row has four boxed sequence cells and one question-mark cell.
- The bottom row has four fixed option boxes labeled `A` through `D`.
- Icon sizes follow a constant pixel-size step of at least 12 pixels.

## Trace

- `execution_trace.full_sequence_values` stores the complete size sequence in pixels.
- `execution_trace.missing_index` stores the hidden top-row position.
- `execution_trace.option_values_by_label` maps each option label to its icon size.
