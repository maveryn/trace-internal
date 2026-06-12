# `task_pages__schema__relationship_cardinality_label`

## 1) Identity
1. Domain: `pages`
2. Scene: `schema`
3. Scene id: `schema`
4. Task id: `task_pages__schema__relationship_cardinality_label`
5. Objective: Identify the normalized cardinality class shown by relationship endpoint markers between two tables.

## 2) Scene + Task Contract
1. Supported `query_id` values: `relationship_cardinality_between_tables`
2. `answer_gt.type`: `string`
3. Supported answers: `one_to_one`, `one_to_many`, `optional_many`
4. `annotation_gt.type`: `keyed_bbox_map`
5. Annotation witness policy: Use `source_table`, `target_table`, `source_cardinality_marker`, and `target_cardinality_marker` boxes.
6. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_schema_v0`
2. Prompt templates come from `prompts/pages/schema/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The sampled relationship must have a unique directed source/target table pair.
4. The generator constructs valid samples and rejects invalid samples instead of semantically relaxing constraints.
