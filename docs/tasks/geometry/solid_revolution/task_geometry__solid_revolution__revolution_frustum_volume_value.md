# `task_geometry__solid_revolution__revolution_frustum_volume_value`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_revolution`
3. Task id: `task_geometry__solid_revolution__revolution_frustum_volume_value`
4. Supported `query_id` values: `single`
5. Answer schema: `decimal_value_1dp`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires multiple role-bound boxes for the generating shape, axis, solid preview, target cue, and visible measurement labels)

## Program Contract
- `solve_formula(visible_solid_revolution_measurements, formula_schema=frustum_volume_from_trapezoid, target=volume); scene=solid_revolution; scope=revolution_frustum_volume_value`

## Query IDs
- `single`: a right trapezoid is rotated 360 degrees around the marked side; solve the resulting frustum volume from the visible height and radii.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/solid_revolution/geometry_solid_revolution_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
The annotation is a `bbox_map` with role-bound pixel boxes:

- `generating_shape`
- `rotation_axis`
- `solid_preview`
- `target_volume_cue`
- `height_label`
- `top_radius_label`
- `bottom_radius_label`

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_revolution.yaml`
- Prompt bundle: `prompts/geometry/solid_revolution/geometry_solid_revolution_v1.json`
- Task module: `trace/tasks/geometry/solid_revolution/revolution_frustum_volume_value.py`
