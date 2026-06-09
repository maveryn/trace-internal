# `task_geometry__sector__sector_area_value_area_from_radius_and_complement_angle`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `sector`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `area_from_radius_and_complement_angle`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_sector_measurements, derivation_rule=area_from_radius_and_complement_angle, output_role=area_measure); scene=sector; scope=sector_area_value_area_from_radius_and_complement_angle`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/sector_formula.py`
