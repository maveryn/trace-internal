# `task_geometry__solid_revolution__revolution_cone_volume_value`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_revolution`
3. Query id: `single`
4. Answer schema: `decimal_value_1dp`
5. Annotation schema: `bbox_map`

## Program Contract
- `solve_formula(visible_solid_revolution_measurements, formula_schema=cone_volume_from_right_triangle, target=volume); scene=solid_revolution; scope=revolution_cone_volume_value`

## Query IDs
- `single`: a right triangle is rotated 360 degrees around the marked leg; solve the resulting cone volume from the visible height and slant height.

## Prompt Bundle
- Bundle: `geometry_solid_revolution_v1`
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
The annotation is a `bbox_map` with role-bound pixel boxes:

- `generating_shape`
- `rotation_axis`
- `solid_preview`
- `target_volume_cue`
- `height_label`
- `slant_height_label`

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_revolution.yaml`
- Task module: `trace/tasks/geometry/solid_revolution/revolution_cone_volume_value.py`
