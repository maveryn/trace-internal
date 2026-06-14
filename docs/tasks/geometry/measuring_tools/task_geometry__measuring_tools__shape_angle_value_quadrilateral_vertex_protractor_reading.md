# `task_geometry__measuring_tools__shape_angle_value_quadrilateral_vertex_protractor_reading`

## Contract
1. Domain: `geometry`
2. Scene id: `measuring_tools`
5. Query ids: `quadrilateral_vertex_protractor_reading`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_measuring_tools_measurements, derivation_rule=quadrilateral_vertex_protractor_reading, output_role=angle_measure); scene=measuring_tools; scope=shape_angle_value_quadrilateral_vertex_protractor_reading`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `measuring_tools`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation must be a keyed point map with `angle_vertex`, `baseline_ray_point`, `target_ray_point`, and `protractor_reading_tick`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measuring_tools.yaml`
- Task module: `trace/tasks/geometry/measuring_tools/shape_angle_value_quadrilateral_vertex_protractor_reading.py`
