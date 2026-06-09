# `task_geometry__angle_relations__algebraic_angle_value_triangle_double_extension_expression`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `angle_relations`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `triangle_double_extension_expression`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_angle_relations_measurements, derivation_rule=triangle_double_extension_expression, output_role=angle_measure); scene=angle_relations; scope=algebraic_angle_value_triangle_double_extension_expression`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
