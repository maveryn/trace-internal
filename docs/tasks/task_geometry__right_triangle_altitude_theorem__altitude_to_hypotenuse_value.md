# `task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value`

## Contract
1. Domain: `geometry`
2. Scene id: `right_triangle_altitude_theorem`
3. Scene id: `right_triangle_altitude_theorem`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `altitude_from_split_hypotenuse` or `missing_projection_from_altitude`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_right_triangle_altitude_to_hypotenuse, unknown_role=altitude_or_projection_length, formula_schema=altitude_geometric_mean); scene=right_triangle_altitude_theorem; scope=altitude_to_hypotenuse_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_right_triangle_altitude_theorem_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the right-angle vertex, altitude foot, and hypotenuse endpoints:

- `right_angle_vertex`
- `altitude_foot`
- `hypotenuse_left_endpoint`
- `hypotenuse_right_endpoint`

Numeric labels, vertex labels, right-angle markers, and the unknown marker remain visible annotations plus verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/right_triangle_altitude_theorem.yaml`
- Task module: `trace/tasks/geometry/right_triangle_altitude_theorem/altitude_to_hypotenuse_value.py`
