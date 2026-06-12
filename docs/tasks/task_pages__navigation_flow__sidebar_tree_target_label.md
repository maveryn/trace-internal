# `task_pages__navigation_flow__sidebar_tree_target_label`

## 1) Identity
1. Domain: `pages`
2. Scene: `relation`
3. Scene id: `navigation_flow`
4. Task id: `task_pages__navigation_flow__sidebar_tree_target_label`
5. Objective: Identify the sidebar item reached by a visible sidebar tree path.

## 2) Scene + Task Contract
1. Supported `query_id` values: `sidebar_tree_target_label`
2. `answer_gt.type`: `option_letter`
3. `annotation_gt.type`: `keyed_bbox_map`
4. Annotation witness policy: Sidebar-section, sidebar-group, and target-item boxes.
5. `query_id` is retained as internal replay metadata; this public task id is the sampling unit.

## 3) Prompt Contract
1. `prompt_bundle_id`: `pages_relation_v0`
2. Prompt templates come from `prompts/pages/relation/` and are rendered with the scene layer plus task/query layer.
3. Output modes: `answer_only` and `answer_and_annotation`.
4. Annotation examples must match the role names and annotation type above.

## 4) Determinism + Constraints
1. Generation is deterministic for `instance_seed` plus params.
2. Answers and annotation come from the same rendered trace payload.
3. The generator constructs unique final answers and rejects invalid samples instead of semantically relaxing constraints.
