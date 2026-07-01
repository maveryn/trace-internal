# `task_geometry__coordinate_conversion__cartesian_component_value`

## Contract
1. Domain: `geometry`
2. Scene id: `coordinate_conversion`
3. Query id: `x_from_polar_point`, `y_from_polar_point`
4. Answer schema: `number`
5. Annotation schema: scalar `segment`

## Program Contract
- `convert_polar_point_to_cartesian_component(ray=OP, radius=r, angle_degrees=theta, requested_component in {x, y}); scene=coordinate_conversion; scope=cartesian_component_value`

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/coordinate_conversion/geometry_coordinate_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the pixel segment from `O` to `P`. The displayed radius and angle, computed Cartesian components, candidate answer support, and formula trace remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate_conversion.yaml`
- Task module: `trace/tasks/geometry/coordinate_conversion/cartesian_component_value.py`
