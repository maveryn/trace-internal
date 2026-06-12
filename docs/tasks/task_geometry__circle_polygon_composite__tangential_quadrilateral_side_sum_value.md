# `task_geometry__circle_polygon_composite__tangential_quadrilateral_side_sum_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_polygon_composite`
3. Scene id: `circle_polygon_composite`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `opposite_side_sum_from_tangent_quadrilateral`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(tangential_quadrilateral, unknown_role=opposite_side_sum, formula_schema=opposite_side_sums_equal); scene=circle_polygon_composite; scope=tangential_quadrilateral_side_sum_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_polygon_composite_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed points for the four vertices, four side tangency points, and incircle center. Required keys are `vertex_A`, `vertex_B`, `vertex_C`, `vertex_D`, `tangent_AB`, `tangent_BC`, `tangent_CD`, `tangent_DA`, and `incircle_center`. Numeric side-length labels are visible annotations plus verifier metadata, not annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_polygon_composite.yaml`
- Task module: `trace/tasks/geometry/circle_polygon_composite/tangential_quadrilateral_side_sum_value.py`
