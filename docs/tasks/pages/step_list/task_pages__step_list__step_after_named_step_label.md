# `task_pages__step_list__step_after_named_step_label`

## Identity
1. Domain: `pages`
2. Scene id: `step_list`
3. Source scene: `step_list`
4. Task id: `task_pages__step_list__step_after_named_step_label`

## Program Contract
1. Program schema: `step_list_step_after_named_step_label(source_step_title) -> next_step_title; scene=step_list; scope=step_after_named_step_label`
2. Scene: `step_list`
3. Scope: one rendered numbered step list with visible step numbers, titles, and detail lines.
4. Supported `query_id`: `single`
5. Answer schema: `string`
6. Annotation schema: `bbox`
7. Annotation witness: one box around the answer step title.
8. Query arguments: visible source step title.
9. Render arguments: step count, scene layout variant, source step index, visual style, and post-render noise.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v1`
2. Scene key: `step_list`
3. Task key: `step_lookup_query`
4. Prompt query key: `step_after_named_step`
5. Trace records `query_id=single`, `prompt_query_key=step_after_named_step`, `source_query_id=step_after_named_step`, source and target step records, final title bboxes, source-title support bbox metadata, sampled layout metadata, and scalar projected annotation.
6. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.
