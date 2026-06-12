# `task_pages__step_list__step_after_named_step_label`

## 1) Identity
1. Domain: `pages`
2. Scene: `step_list`
3. Scene id: `step_list`
4. Task id: `task_pages__step_list__step_after_named_step_label`
5. Objective: Return the step title immediately after a named source step.

## 2) Scene + Task Contract
1. Supported `query_id` values: `step_after_named_step`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Source step-title and target step-title boxes.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_step_list_v0`
2. Prompt templates come from `prompts/pages/step_list/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
