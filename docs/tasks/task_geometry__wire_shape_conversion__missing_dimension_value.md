# `task_geometry__wire_shape_conversion__missing_dimension_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `wire_shape_conversion`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `same_wire_circle_to_trapezoid_side`, `same_wire_polygon_to_rectangle_side`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(equal_wire_length_shape_to_shape_conversion, target=missing_target_side, formula_schema=wire_shape_conversion_missing_dimension); scene=wire_shape_conversion`

## Prompt Bundle
- Prompt text is loaded from `geometry_wire_shape_conversion_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_wire_shape_bbox`, `target_shape_bbox`, `source_dimension_region_bbox`, `target_known_dimension_region_bbox`, and `target_unknown_side_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/wire_shape_conversion.py`
