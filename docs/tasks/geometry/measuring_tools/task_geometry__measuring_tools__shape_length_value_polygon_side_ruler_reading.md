# `task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading`

## Contract
1. Domain: `geometry`
2. Scene id: `measuring_tools`
5. Supported `query_id`s: `single`
6. Answer schema: `integer`
7. Annotation schema: `point_map`

## Program Contract
- `read_visible_measurement_tool(tool=ruler, target=polygon_side, unit=centimeters, output_role=length_measure); scene=measuring_tools; scope=shape_length_value_polygon_side_ruler_reading`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `measuring_tools`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation must be a keyed point map with `measure_start`, `measure_end`, `ruler_start_tick`, and `ruler_end_tick`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measuring_tools.yaml`
- Task module: `trace/tasks/geometry/measuring_tools/shape_length_value_polygon_side_ruler_reading.py`
