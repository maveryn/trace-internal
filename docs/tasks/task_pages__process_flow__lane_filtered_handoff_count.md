# `task_pages__process_flow__lane_filtered_handoff_count`

## 1) Identity
1. Domain: `pages`
2. Task group: `process_flow`
3. Scene id: `process_flow`
4. Task id: `task_pages__process_flow__lane_filtered_handoff_count`
5. Objective: Count visible handoff arrows filtered by a named lane's involvement or outgoing direction.

## 2) Scene + Task Contract
1. Supported `query_id` values: `lane_outgoing_handoff_count`, `lane_involved_handoff_count`
2. `answer_gt.type`: `integer`
3. `annotation_gt.type`: `point_pair_set`
4. Annotation witness policy: One pixel point pair for every counted handoff arrow.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_process_flow_v0`
2. Prompt templates come from `prompts/pages/process_flow/`.
3. Output modes: `answer_only` and `answer_and_annotation`.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
