# `task_geometry__wire_shape_conversion__wire_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `wire_shape_conversion`
3. Task id: `task_geometry__wire_shape_conversion__wire_length_value`
4. Supported `query_id` values: `trapezoid_wire_length`, `parallelogram_wire_length`, `circle_wire_length_from_area`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires role-bound boxes for the wire shape and its dimension readout region)

## Program Contract
- `solve_formula(visible_wire_shape_measurements, target=total_wire_length, formula_schema=wire_shape_perimeter_or_circumference); scene=wire_shape_conversion; scope=wire_length_value`

## Query Semantics
- `trapezoid_wire_length` asks for total wire length around an isosceles trapezoid from shown top, bottom, and equal-side lengths.
- `parallelogram_wire_length` asks for total wire length around a parallelogram from shown base and side lengths.
- `circle_wire_length_from_area` asks for circular wire length from shown circle area using `pi=3`.
- Numeric dimensions, case pool index, diagram style, palette, and render retry index are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a pixel-space bbox map with `wire_shape_bbox` and `dimension_region_bbox`. The map binds the visible wire shape separately from its measurement labels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/wire_shape_conversion.yaml`
- Prompt bundle: `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`
- Task module: `trace/tasks/geometry/wire_shape_conversion/wire_length_value.py`
