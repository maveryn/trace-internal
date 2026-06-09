# `task_pages__record_table__enabled_action_for_type_count`

## 1) Identity
1. Domain: `pages`
2. Task group: `counting`
3. Scene id: `record_table`
4. Task id: `task_pages__record_table__enabled_action_for_type_count`
5. Objective: Count record-table rows of one visible type whose visible action is enabled.

## 2) Scene + Task Contract
1. Supported `query_id` values: `enabled_action_for_type_count`
2. `answer_gt.type`: `integer`
3. `annotation_gt.type`: `bbox_set`
4. Annotation witness policy: Full table-row boxes for every counted row.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_counting_v0`
2. Prompt templates come from `prompts/pages/counting/`.
3. Output modes: `answer_only` and `answer_and_annotation`.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
