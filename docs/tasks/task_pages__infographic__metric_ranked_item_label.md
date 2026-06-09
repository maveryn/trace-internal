# `task_pages__infographic__metric_ranked_item_label`

## 1) Identity
1. Domain: `pages`
2. Task group: `infographic`
3. Scene id: `infographic`
4. Task id: `task_pages__infographic__metric_ranked_item_label`
5. Objective: Identify the metric card at a requested rank by printed value.

## 2) Scene + Task Contract
1. Supported `query_id` values: `nth_highest_metric_label`, `nth_lowest_metric_label`, `nth_highest_metric_in_section_label`, `nth_lowest_metric_in_section_label`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Global queries use `target_metric` and `target_value` boxes. Section-scoped queries additionally use the `section_title` box.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_infographic_v0`
2. Prompt templates come from `prompts/pages/infographic/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. Metric values are unique within the queried scope so the requested rank has one answer.
4. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
