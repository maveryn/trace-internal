# `task_geometry__special_quadrilateral__diagonal_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `special_quadrilateral`
3. Task id: `task_geometry__special_quadrilateral__diagonal_angle_value`
4. Supported `query_id`: `rhombus_vertex_angle_bisected_by_diagonal`, `kite_vertex_angle_bisected_by_symmetry_diagonal`, `rhombus_diagonal_perpendicular_complement`
5. Answer schema: `integer`
6. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_special_quadrilateral_diagonal_relation, unknown_role=target_angle, formula_schema=diagonal_angle_theorem); scene=special_quadrilateral; scope=diagonal_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_special_quadrilateral_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation maps each visible witness point label to its pixel point `[x,y]`.
The keys are the visible point labels required by the active construction: `A`, `B`, `C`, `D`, and `O` when a diagonal intersection is shown.
The task keeps `point_map` rather than scalar annotation because multiple role-bound labeled points are required.

## Query Semantics
- `rhombus_vertex_angle_bisected_by_diagonal`: a rhombus diagonal bisects a vertex angle.
- `kite_vertex_angle_bisected_by_symmetry_diagonal`: a kite symmetry diagonal bisects a vertex angle.
- `rhombus_diagonal_perpendicular_complement`: rhombus diagonals are perpendicular, so the target angle complements the shown angle.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/special_quadrilateral.yaml`
- Task module: `trace/tasks/geometry/special_quadrilateral/diagonal_angle_value.py`
