# `task_pages__instruction_panel__step_for_control_pair_label`

## Identity
1. Domain: `pages`
2. Scene id: `instruction_panel`
3. Source scene: `step_list`
4. Task id: `task_pages__instruction_panel__step_for_control_pair_label`

## Contract
1. Objective: find the unique visible step containing two named control-chip labels and return that step number.
2. Branch metadata: `query_id`
3. `query_id`: `step_for_control_pair_label`
4. Answer type: `integer`
5. Annotation type: `keyed_bbox_map` with `first_control`, `second_control`, and `target_step_number` boxes.
6. Query knobs: step count, control count, controls per step, target control pair, target step, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v0`
2. Scene key: `instruction_panel`
3. Task key: `instruction_panel_query`
4. Internal prompt variant key: `step_for_control_pair_label`
5. Trace records numbered steps, control labels, final chip bboxes, step-number badge bboxes, sampled style metadata, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized instruction-panel render metadata.
