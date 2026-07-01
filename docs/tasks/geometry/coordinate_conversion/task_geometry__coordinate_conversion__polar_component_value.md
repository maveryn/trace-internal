# `task_geometry__coordinate_conversion__polar_component_value`

## Contract
1. Domain: `geometry`
2. Scene id: `coordinate_conversion`
3. Query id: `radius_from_cartesian_point`, `angle_from_cartesian_point`
4. Answer schema: `number`
5. Annotation schema: scalar `point`

## Program Contract
- `convert_cartesian_point_to_polar_component(point=P, requested_component in {radius, angle_degrees}); scene=coordinate_conversion; scope=polar_component_value`

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/coordinate_conversion/geometry_coordinate_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the pixel point at labeled point `P`. Grid coordinates, radius, angle, candidate answer support, and formula trace remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate_conversion.yaml`
- Task module: `trace/tasks/geometry/coordinate_conversion/polar_component_value.py`
