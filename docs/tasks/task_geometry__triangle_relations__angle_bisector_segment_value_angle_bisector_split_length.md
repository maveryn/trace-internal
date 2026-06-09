# `task_geometry__triangle_relations__angle_bisector_segment_value_angle_bisector_split_length`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `angle_bisector_split_length`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_triangle_relations_measurements, derivation_rule=angle_bisector_split_length, output_role=length_measure); scene=triangle_relations; scope=angle_bisector_segment_value_angle_bisector_split_length`

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
