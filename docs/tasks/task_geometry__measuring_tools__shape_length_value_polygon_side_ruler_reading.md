# `task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `measuring_tools`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `polygon_side_ruler_reading`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_measuring_tools_measurements, unknown_role=length_measure, formula_schema=polygon_side_ruler_reading); scene=measuring_tools; scope=shape_length_value_polygon_side_ruler_reading`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation must be a keyed point map with `measure_start`, `measure_end`, `ruler_start_tick`, and `ruler_end_tick`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/measuring_tools.py`
