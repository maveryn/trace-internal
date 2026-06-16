# `task_geometry__circle_polygon_composite__square_circle_tangent_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_polygon_composite`
4. Query ids: `square_incircle_tangent_angle`, `rectangle_semicircle_tangent_angle`
5. Answer schema: `integer_value`
6. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(square_incircle_or_rectangle_semicircle_tangent_construction, unknown_role=target_angle, formula_schema=tangent_radius_perpendicular_angle_transfer); scene=circle_polygon_composite; scope=square_circle_tangent_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_polygon_composite_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed points for the visible construction labels. Required keys are `A`, `B`, `C`, `D`, `O`, and `T`. Numeric angle labels and angle arcs are visible diagram marks plus verifier metadata, not annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_polygon_composite.yaml`
- Task module: `trace/tasks/geometry/circle_polygon_composite/square_circle_tangent_angle_value.py`
