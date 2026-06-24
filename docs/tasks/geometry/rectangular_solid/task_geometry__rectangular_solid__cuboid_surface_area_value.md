# `task_geometry__rectangular_solid__cuboid_surface_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `rectangular_solid`
3. Task id: `task_geometry__rectangular_solid__cuboid_surface_area_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task always needs six role-bound dimension-guide endpoints)

## Program Contract
- `solve_formula(cuboid_dimension_measurements, unknown_role=surface_area, formula_schema=cuboid_total_surface_area); scene=rectangular_solid; scope=cuboid_surface_area_value`

## Query Semantics
- `single` asks for the total surface area of the cuboid from the visible length, width, and height labels.
- The sampled dimensions, view jitter, face palette, style, font, and render retry index are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed points for the visible dimension-guide endpoints: `length_segment_start`, `length_segment_end`, `width_segment_start`, `width_segment_end`, `height_segment_start`, and `height_segment_end`. Numeric labels and the surface-area readout marker remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/rectangular_solid.yaml`
- Prompt bundle: `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`
- Task module: `trace/tasks/geometry/rectangular_solid/cuboid_surface_area_value.py`
