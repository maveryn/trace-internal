# `task_icons__sequence_strip__hue_progression_completion_label`

## Program Contract

`selection.sequence_completion(scene=sequence_strip, scope=four_cell_icon_sequence_with_visual_options, attribute=hue, rule=constant_hue_step, missing_role=question_mark_cell, output=option_label)`

## Identity

- Domain: `icons`
- Scene id: `sequence_strip`
- Task id: `task_icons__sequence_strip__hue_progression_completion_label`
- Module: `trace/tasks/icons/sequence_strip/hue_progression_completion_label.py`
- Prompt bundle: `icons_sequence_strip_v1`

## Contract

- Supported `query_id` values: `single`.
- Answer schema: `string`, one of `A`, `B`, `C`, or `D`.
- Annotation schema: scalar `bbox` around the correct bottom-row option box.
- The top row has four boxed sequence cells and one question-mark cell.
- The bottom row has four fixed option boxes labeled `A` through `D`.
- Icon hues follow a constant step in HSV hue space; saturation and value stay fixed.

## Trace

- `execution_trace.full_sequence_values` stores the complete hue sequence in degrees.
- `execution_trace.missing_index` stores the hidden top-row position.
- `execution_trace.option_values_by_label` maps each option label to its hue in degrees.
- `execution_trace.hue_rgb_by_value` records the rendered RGB for each sampled hue.
