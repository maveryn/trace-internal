# `task_geometry__polygon_angle_chase__symmetry_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `polygon_angle_chase`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `rectangle_diagonal_angle`, `reflection_axis_angle`, `isosceles_base_angle_chain`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_symmetry_angle_measurements, derivation_rule=symmetry_equal_angle_relations, output_role=angle_measure); scene=polygon_angle_chase; scope=symmetry_angle_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points at the target angle vertex and the role-bound supporting construction points needed for the symmetry or equal-angle relation. Visible degree labels, right-angle marks, equal-side ticks, and symmetry-axis marks are annotations plus verifier metadata, not separate public annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_polygon_angle_chase_v0.json`
- Task module: `trace/tasks/geometry/measurement/polygon_angle_chase.py`
