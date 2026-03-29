# `task_geometry_transformation_match`

## 1) Identity
1. Domain: `geometry`
2. Task group: `transformation`
3. Task id: `task_geometry_transformation_match`
4. Objective: identify the labeled polygon that matches the requested Euclidean transformation of the `Reference`.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `triangle`
   - `quadrilateral`
2. Supported `query_variant` values:
   - `translation_match`
   - `reflection_match`
   - `rotation_match`
3. Scene scaffold:
   - one graph-paper scene,
   - one `Reference` polygon,
   - one explicit transformation cue,
   - six labeled candidate polygons `A..F`.
4. `answer_gt.type`: `option_letter`
5. `evidence_gt.type`: `graph_point_set`

## 3) Prompt contract
1. Bundle: `geometry_transformation_v1`
2. Task-family stem introduces one graph-paper transformation scene.
3. `task_variant` carries the question wording:
   - `translation_match` asks for the polygon translated by the shown vector,
   - `reflection_match` asks for the polygon reflected across line `l`,
   - `rotation_match` asks for the polygon after the shown rotation about point `O`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the winning polygon’s unordered vertex set in graph-paper coordinates.
2. `projected_evidence` preserves both graph- and pixel-space point projections for the winning polygon vertices.
3. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `winner_label`
   - cue-specific fields such as `translation_vector` or `rotation_mode`
4. Candidate polygons remain labeled in trace/render metadata so review workbooks can show the winning option label even though prompt evidence stays coordinate-grounded.

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Exactly one candidate matches the requested transformation by construction.
3. Candidate labels are balanced independently of slot position so answer-label distribution does not collapse to one visible location.
4. `rotation_match` only uses rotation cues whose inverse-mapped Reference stays fully visible on the graph paper.

## 6) Complexity + tests
1. Complexity uses the geometry transformation-family criteria:
   - `visual_scan`
   - `transformation_reasoning`
   - `ambiguity`
   - `output_burden`
2. Behavior tests: `tests/test_geometry_transformation_match_tasks.py`
3. Contract/config tests: `tests/test_geometry_transformation_match_contracts.py`, `tests/test_geometry_transformation_task_group_config.py`
