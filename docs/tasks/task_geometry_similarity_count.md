# `task_geometry_similarity_count`

## 1) Identity
1. Domain: `geometry`
2. Task group: `similarity`
3. Task id: `task_geometry_similarity_count`
4. Objective: count how many labeled polygons satisfy the requested similarity relation with the `Reference`.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `triangle`
   - `quadrilateral`
2. Supported `query_variant` values:
   - `congruent_count`
   - `similar_count`
3. Scene scaffold:
   - one graph-paper scene,
   - one `Reference` polygon,
   - five labeled candidate polygons `A..E`.
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `label_set`

## 3) Prompt contract
1. Bundle: `geometry_similarity_v1`
2. Task-family stem introduces one graph-paper reference/candidate scene.
3. `task_variant` carries the question wording:
   - `congruent_count` asks how many labeled polygons are congruent to the `Reference`,
   - `similar_count` asks how many labeled polygons are similar to the `Reference`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `label_set` of every matching candidate polygon label.
2. `projected_evidence` preserves those labels plus candidate-center points and candidate bboxes in pixel space for review.
3. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `target_count`
   - `matching_labels`
4. The count only applies to labeled candidates `A..E`; the `Reference` polygon itself is not counted.

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Candidate labels are fixed to `A..E`, while the matching subset is sampled independently from slot position.
3. `congruent_count` uses rigid-transform matches only; distractors may still be merely similar but not congruent.
4. `similar_count` always keeps all non-matching candidates genuinely non-similar by construction.
5. `target_count` currently uses support `0..5`, so the matching set may span anywhere from no candidates to all five labeled candidates.

## 6) Complexity + tests
1. Complexity uses the geometry similarity-family criteria:
   - `visual_scan`
   - `similarity_reasoning`
   - `ambiguity`
   - `output_burden`
2. Behavior tests: `tests/test_geometry_consolidated_tasks.py`
3. Contract/config tests: `tests/test_geometry_similarity_count_contracts.py`, `tests/test_geometry_similarity_task_group_config.py`
