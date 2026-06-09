# `task_geometry__rectangular_solid__cuboid_surface_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `rectangular_solid`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `surface_area_from_dimensions`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_cuboid_dimension_measurements, unknown_role=surface_area, formula_schema=cuboid_surface_area); scene=rectangular_solid; scope=cuboid_surface_area_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_rectangular_solid_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed point map with visible dimension-guide endpoints: `length_segment_start`, `length_segment_end`, `width_segment_start`, `width_segment_end`, `height_segment_start`, and `height_segment_end`. Numeric labels, surface-area readout text, dimension arrows, and the `?` marker are visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/rectangular_solid.py`
