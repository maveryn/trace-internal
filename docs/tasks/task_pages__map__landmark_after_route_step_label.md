# `task_pages__map__landmark_after_route_step_label`

## 1) Identity
1. Domain: `pages`
2. Task group: `map`
3. Scene id: `map`
4. Task id: `task_pages__map__landmark_after_route_step_label`
5. Objective: Identify the landmark reached after a named step on the visible route.

## 2) Scene + Task Contract
1. Supported `query_id` values: `landmark_after_route_step`
2. `answer_gt.type`: `string`
3. `annotation_gt.type`: `bbox_sequence`
4. Annotation witness policy: Ordered route landmark boxes supporting the route-step lookup.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_map_v0`
2. Prompt templates come from `prompts/pages/map/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
