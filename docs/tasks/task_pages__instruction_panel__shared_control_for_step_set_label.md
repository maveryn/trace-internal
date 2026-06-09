# `task_pages__instruction_panel__shared_control_for_step_set_label`

## Identity
1. Domain: `pages`
2. Scene id: `instruction_panel`
3. Source task group: `step_list`
4. Task id: `task_pages__instruction_panel__shared_control_for_step_set_label`

## Contract
1. Objective: find a referenced set of visible step numbers and return the exact control-chip label common to every referenced step.
2. Branch metadata: `query_id`
3. `query_id`: `shared_control_for_step_set_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_set_map` with `step_numbers` and `shared_control_chips` bbox arrays.
6. Query knobs: step count, control count, controls per step, step-set size, target step set, target control, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v0`
2. Scene key: `instruction_panel`
3. Task key: `instruction_panel_query`
4. Internal prompt variant key: `shared_control_for_step_set_label`
5. Trace records numbered steps, control labels, final chip bboxes, step-number badge bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized instruction-panel render metadata.
