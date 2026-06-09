# `task_geometry__circle_polygon_composite__square_circle_tangent_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `circle_polygon_composite`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `square_incircle_tangent_angle`, `square_semicircle_tangent_angle`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(square_or_semicircle_tangent_construction, unknown_role=target_angle, formula_schema=tangent_radius_perpendicular_angle_transfer); scene=circle_polygon_composite; scope=square_circle_tangent_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_polygon_composite_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed points for the shape corners, circle center, tangent point, known angle witness, and target angle witness. Required keys are `shape_corner_A`, `shape_corner_B`, `shape_corner_C`, `shape_corner_D`, `circle_center`, `tangent_point`, `known_angle_vertex`, `known_angle_reference_point`, `target_angle_vertex`, and `target_reference_point`. Numeric angle labels and angle arcs are visible annotations plus verifier metadata, not annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/circle_polygon_composite.py`
