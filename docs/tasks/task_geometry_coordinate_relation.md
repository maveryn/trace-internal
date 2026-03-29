# `task_geometry_coordinate_relation`

## 1) Identity
1. Domain: `geometry`
2. Task group: `coordinate`
3. Task id: `task_geometry_coordinate_relation`
4. Objective: reason over coordinate-plane segments, marked points, or lattice polygons on graph paper and answer one relation query.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `segment_set`
   - `line_points`
   - `quadrant_points`
   - `polygon_lattice`
2. Supported `query_variant` values:
   - `parallel_count`
   - `perpendicular_count`
   - `collinear_count`
   - `same_quadrant_count`
   - `point_in_shape_count`
3. Scene scaffolds:
   - `segment_set` shows reference segment `AB` plus six unlabeled candidate segments on a centered `-10..10` graph-paper window,
   - `line_points` shows labeled points `A` and `B` plus unlabeled dot points on a centered `-10..10` graph-paper window,
   - `quadrant_points` shows one X-marked reference point plus unlabeled dot points,
   - `polygon_lattice` shows one unlabeled polygon drawn on graph paper.
4. `answer_gt.type` is `integer` for every `query_variant`.
5. `evidence_gt.type` is `graph_point_set` for every `query_variant`.

## 3) Prompt contract
1. Bundle: `geometry_coordinate_v1`
2. Task-family stem introduces one graph-paper coordinate scene.
3. `task_variant` carries the question wording:
   - `parallel_count` asks how many unlabeled segments are parallel to `AB`,
   - `perpendicular_count` asks how many unlabeled segments are perpendicular to `AB`,
   - `collinear_count` asks how many dot points lie on the same line as `A` and `B`,
   - `same_quadrant_count` asks how many dot points lie in the same quadrant as the X-marked point,
   - `point_in_shape_count` asks how many integer lattice points lie strictly inside the shown polygon.

## 4) Evidence + trace contract
1. Segment-count variants use prompt-facing `graph_point_set` evidence for every endpoint of every segment that satisfies the requested relation to `AB`.
2. `collinear_count` uses prompt-facing unordered `graph_point_set` evidence for the dot points that lie on the same line as `A` and `B`.
3. `same_quadrant_count` uses prompt-facing unordered `graph_point_set` evidence for the dot points that share a quadrant with the X-marked point.
4. `point_in_shape_count` uses prompt-facing `graph_point_set` evidence for every integer lattice point strictly inside the polygon.
4. `projected_evidence` preserves pixel-space projections for review:
   - matching segment endpoint points for segment-count variants,
   - matching collinear point centers for `collinear_count`,
   - matching point centers for `same_quadrant_count`,
   - strict interior lattice-point projections for `point_in_shape_count`.
5. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record:
   - `scene_variant`
   - `query_variant`
   - `target_count` for all variants
   - `matching_segment_ids` for segment-count variants
   - `matching_labels` for `same_quadrant_count`
   - polygon vertices and strict interior lattice points for `point_in_shape_count`

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. `segment_set` scenes sample the target segment and all six candidate segments anywhere inside the centered graph window, enforce the sampled relation count by construction, keep every endpoint away from the graph border, and reject any segment placement that intersects another segment.
3. `line_points` scenes sample `A`, `B`, and the dot points from the same centered graph window, keep all points at least one lattice step off the border, and exclude `A`/`B` themselves from both the answer and the evidence.
4. `same_quadrant_count` excludes the X-marked reference point from both the answer and the evidence.
5. `point_in_shape_count` samples one non-rectangular lattice polygon whose strict interior lattice-point count is realized exactly by construction.
6. Segment, line-point, quadrant, and polygon scenes all use fixed `20 x 20` graph-paper windows.
7. Count targets are balanced independently of the visible slot order.

## 6) Complexity + tests
1. Complexity uses the geometry coordinate-family criteria:
   - `visual_scan`
   - `coordinate_reasoning`
   - `ambiguity`
   - `output_burden`
2. Behavior tests: `tests/test_geometry_consolidated_tasks.py`
3. Contract/config tests: `tests/test_geometry_coordinate_relation_contracts.py`, `tests/test_geometry_coordinate_relation_task_group_config.py`
