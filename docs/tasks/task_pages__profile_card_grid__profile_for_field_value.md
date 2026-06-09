# `task_pages__profile_card_grid__profile_for_field_value`

## 1) Identity
1. Domain: `pages`
2. Task group: `document_lookup`
3. Scene id: `profile_card_grid`
4. Task id: `task_pages__profile_card_grid__profile_for_field_value`
5. Objective: Find the profile name whose visible field has a requested value.

## 2) Scene + Task Contract
1. Supported `query_id` values: `profile_for_field_value`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Role-keyed boxes for profile name, field label, and field value.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_document_lookup_v0`
2. Prompt templates come from `prompts/pages/document_lookup/`.
3. Output modes: `answer_only` and `answer_and_annotation`.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
