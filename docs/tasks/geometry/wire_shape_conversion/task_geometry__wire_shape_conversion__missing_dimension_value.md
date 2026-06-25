# `task_geometry__wire_shape_conversion__missing_dimension_value`

## Contract
1. Domain: `geometry`
2. Scene id: `wire_shape_conversion`
3. Task id: `task_geometry__wire_shape_conversion__missing_dimension_value`
4. Supported `query_id` values: `same_wire_circle_to_trapezoid_side`, `same_wire_polygon_to_rectangle_side`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires multiple role-bound source, target, known-dimension, and unknown-side boxes)

## Program Contract
- `solve_formula(equal_wire_length_shape_to_shape_conversion, target=missing_target_side, formula_schema=wire_shape_conversion_missing_dimension); scene=wire_shape_conversion; scope=missing_dimension_value`

## Query Semantics
- `same_wire_circle_to_trapezoid_side` asks for the missing equal side of a target isosceles trapezoid made from the same circular wire.
- `same_wire_polygon_to_rectangle_side` asks for the missing rectangle side when the source trapezoid wire is reshaped into a rectangle.
- Numeric dimensions, case pool index, diagram style, palette, and render retry index are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a pixel-space bbox map with `source_wire_shape_bbox`, `target_shape_bbox`, `source_dimension_region_bbox`, `target_known_dimension_region_bbox`, and `target_unknown_side_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/wire_shape_conversion.yaml`
- Prompt bundle: `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`
- Task module: `trace/tasks/geometry/wire_shape_conversion/missing_dimension_value.py`
