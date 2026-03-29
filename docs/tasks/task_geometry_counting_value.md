# `task_geometry_counting_value`

## 1) Identity
1. Domain: `geometry`
2. Task group: `counting`
3. Task id: `task_geometry_counting_value`
4. Objective: count how many labeled objects in the scene satisfy the requested geometry class.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `angle`
   - `triangle`
   - `quadrilateral`
   - `mixed_shape`
   - `polygon`
2. Supported `query_variant` values:
   - `acute_angle|right_angle|obtuse_angle`
   - `equilateral_triangle|isosceles_triangle|scalene_triangle|right_triangle|acute_triangle|obtuse_triangle`
   - `square|rectangle_non_square|rhombus_non_square|parallelogram_only`
   - `triangle|quadrilateral|pentagon|hexagon|circle|ellipse`
   - `convex_polygon|concave_polygon`
3. Each `scene_variant` only supports the compatible class queries for that object family.
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `label_set`

## 3) Prompt contract
1. Bundle: `geometry_counting_v1`
2. Prompts remain delegated to the legacy counting prompts so each scene family keeps its established wording and evidence examples.
3. Consolidated trace metadata always records the scene family in `scene_variant` and the counted class in `query_variant`.

## 4) Evidence + trace contract
1. `label_set` evidence remains semantically unordered.
2. `execution_trace`, `query_spec.params`, and `scene_ir.relations` record the consolidated axes plus `legacy_task_id`.
3. Legacy counting-specific fields like class-by-label maps remain intact.

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Incompatible scene/query combinations are rejected.
3. Answer counts and evidence labels still come from the same finalized scene labeling.

## 6) Complexity + tests
1. Complexity components stay counting-family-specific and come from the delegated legacy generator.
2. Determinism/build tests: `tests/test_geometry_consolidated_contracts.py`
3. Behavior/trace tests: `tests/test_geometry_consolidated_tasks.py`
