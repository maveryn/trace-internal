# `task_pages__step_list__step_for_detail_label`

## Identity
1. Domain: `pages`
2. Scene id: `step_list`
3. Source scene: `step_list`
4. Task id: `task_pages__step_list__step_for_detail_label`

## Program Contract
1. Program schema: `step_list_step_for_detail_label(source_step_detail, output_role) -> step_title_or_number; scene=step_list; scope=step_for_detail_label`
2. Scene: `step_list`
3. Scope: one rendered numbered step list with visible step numbers, titles, and detail lines.
4. Supported `query_id` values: `step_title_for_detail`, `step_number_for_detail`
5. Answer schema: `string`
6. Annotation schema: `bbox`
7. Annotation witness: one box around the answer visual: the target title for `step_title_for_detail`, or the target number badge for `step_number_for_detail`.
8. Query arguments: visible source step detail and requested output role.
9. Render arguments: step count, scene layout variant, target detail index, visual style, and post-render noise.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v1`
2. Scene key: `step_list`
3. Task key: `step_lookup_query`
4. Prompt query keys: `step_title_for_detail`, `step_number_for_detail`
5. Trace records the selected semantic `query_id`, matching `prompt_query_key`, `source_query_id`, step records, target step index, final detail/title/number bboxes, source-detail support bbox metadata, sampled layout metadata, and scalar projected annotation.
6. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.
