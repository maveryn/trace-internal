# `task_geometry__special_quadrilateral__diagonal_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `special_quadrilateral`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `rhombus_vertex_angle_bisected_by_diagonal`, `kite_vertex_angle_bisected_by_symmetry_diagonal`, or `rhombus_diagonal_perpendicular_complement`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_special_quadrilateral_diagonal_relation, unknown_role=target_angle, formula_schema=diagonal_angle_theorem); scene=special_quadrilateral; scope=diagonal_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_special_quadrilateral_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points that bind the visible angle and construction roles:

- `target_vertex`
- `support_vertex`
- diagonal endpoint or intersection keys emitted by the active query

Angle labels and theorem identifiers remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/special_quadrilateral.py`
