# `task_pages__infographic__section_total_extrema_difference_value`

## 1) Identity
1. Domain: `pages`
2. Task group: `infographic`
3. Scene id: `infographic`
4. Task id: `task_pages__infographic__section_total_extrema_difference_value`
5. Objective: Compute the difference between extrema-selected section totals.

## 2) Scene + Task Contract
1. Supported `query_id` values: `section_total_extrema_difference`
2. `answer_gt.type`: `integer`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Supporting metric-card boxes keyed by visible metric-card labels.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_infographic_v0`
2. Prompt templates come from `prompts/pages/infographic/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
