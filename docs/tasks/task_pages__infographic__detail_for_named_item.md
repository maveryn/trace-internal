# `task_pages__infographic__detail_for_named_item`

## 1) Identity
1. Domain: `pages`
2. Task group: `infographic`
3. Scene id: `infographic`
4. Task id: `task_pages__infographic__detail_for_named_item`
5. Objective: Read the detail text associated with one named infographic item.

## 2) Scene + Task Contract
1. Supported `query_id` values: `detail_for_named_item`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: The metric-card box keyed by the visible supporting item label.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_infographic_v0`
2. Prompt templates come from `prompts/pages/infographic/`.
3. Output modes: `answer_only` and `answer_and_annotation`.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
