# `task_geometry__wire_shape_conversion__wire_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `wire_shape_conversion`
3. Scene id: `wire_shape_conversion`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `trapezoid_wire_length`, `parallelogram_wire_length`, `circle_wire_length_from_area`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_wire_shape_measurements, target=total_wire_length, formula_schema=wire_shape_perimeter_or_circumference); scene=wire_shape_conversion`

## Prompt Bundle
- Prompt text is loaded from `geometry_wire_shape_conversion_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `wire_shape_bbox` and `dimension_region_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/wire_shape_conversion.yaml`
- Task module: `trace/tasks/geometry/wire_shape_conversion/wire_length_value.py`
