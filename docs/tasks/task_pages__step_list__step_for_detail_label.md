# `task_pages__step_list__step_for_detail_label`

## 1) Identity
1. Domain: `pages`
2. Task group: `step_list`
3. Scene id: `step_list`
4. Task id: `task_pages__step_list__step_for_detail_label`
5. Objective: Return the step title or step number that owns a named visible detail line.

## 2) Scene + Task Contract
1. Supported `query_id` values: `step_title_for_detail`, `step_number_for_detail`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Source step-detail box plus the target step-title or step-number box.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_step_list_v0`
2. Prompt templates come from `prompts/pages/step_list/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. Detail phrases are unique within each generated list; the generator rejects invalid samples instead of semantically relaxing constraints.
