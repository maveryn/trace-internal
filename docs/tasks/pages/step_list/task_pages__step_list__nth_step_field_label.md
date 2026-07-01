# `task_pages__step_list__nth_step_field_label`

## Identity
1. Domain: `pages`
2. Scene id: `step_list`
3. Source scene: `step_list`
4. Task id: `task_pages__step_list__nth_step_field_label`

## Program Contract
1. Program schema: `step_list_nth_step_field_label(step_reference, field_role={title,detail}) -> field_text; scene=step_list; scope=nth_step_field_label`
2. Scene: `step_list`
3. Scope: one rendered numbered step list with visible step numbers, titles, and detail lines.
4. Supported `query_id` values: `nth_step_title`, `nth_step_detail`
5. Answer schema: `string`
6. Annotation schema: `bbox`
7. Annotation witness: one scalar box around the requested visible field: the step title for `nth_step_title`, or the step detail line for `nth_step_detail`.
8. Query arguments: ordinal step reference and requested field role.
9. Render arguments: step count, scene layout variant, ordinal-reference sampling, visual style, and post-render noise.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v1`
2. Scene key: `step_list`
3. Task key: `step_lookup_query`
4. Prompt query keys: `nth_step_title` and `nth_step_detail`
5. Trace records the selected semantic `query_id`, matching `prompt_query_key`, `source_query_id`, step records, target step index, final title/detail bboxes, sampled layout metadata, and scalar projected annotation.
6. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.
