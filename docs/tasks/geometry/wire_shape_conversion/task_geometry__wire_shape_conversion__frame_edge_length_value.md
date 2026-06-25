# `task_geometry__wire_shape_conversion__frame_edge_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `wire_shape_conversion`
3. Task id: `task_geometry__wire_shape_conversion__frame_edge_length_value`
4. Supported `query_id` values: `trapezoid_wire_to_cube_frame`, `parallelogram_wire_to_cuboid_frame`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires multiple role-bound source, target, known-dimension, and unknown-edge boxes)

## Program Contract
- `solve_formula(equal_wire_length_shape_to_frame_conversion, target=missing_frame_edge, formula_schema=wire_shape_conversion_frame_edge); scene=wire_shape_conversion; scope=frame_edge_length_value`

## Query Semantics
- `trapezoid_wire_to_cube_frame` asks for the cube frame edge length when the source trapezoid wire is reused as a 12-edge cube frame.
- `parallelogram_wire_to_cuboid_frame` asks for the cuboid frame height when the source parallelogram wire is reused as a cuboid frame with two known target edge dimensions.
- Numeric dimensions, case pool index, diagram style, palette, and render retry index are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a pixel-space bbox map with `source_wire_shape_bbox`, `target_frame_bbox`, `source_dimension_region_bbox`, `target_known_dimension_region_bbox`, and `target_unknown_edge_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/wire_shape_conversion.yaml`
- Prompt bundle: `prompts/geometry/wire_shape_conversion/geometry_wire_shape_conversion_v1.json`
- Task module: `trace/tasks/geometry/wire_shape_conversion/frame_edge_length_value.py`
