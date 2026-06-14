# `task_geometry__right_triangle_altitude_theorem__leg_projection_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `right_triangle_altitude_theorem`
5. Query id: `leg_from_hypotenuse_projection` or `projection_from_leg_and_hypotenuse`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_right_triangle_leg_projection_relation, unknown_role=leg_or_projection_length, formula_schema=leg_geometric_mean_with_hypotenuse_projection); scene=right_triangle_altitude_theorem; scope=leg_projection_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_right_triangle_altitude_theorem_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target leg endpoint, right-angle vertex, altitude foot, and opposite hypotenuse endpoint:

- `right_angle_vertex`
- `leg_hypotenuse_endpoint`
- `altitude_foot`
- `other_hypotenuse_endpoint`

Numeric labels, vertex labels, right-angle markers, and the unknown marker remain visible annotations plus verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/right_triangle_altitude_theorem.yaml`
- Task module: `trace/tasks/geometry/right_triangle_altitude_theorem/leg_projection_length_value.py`
