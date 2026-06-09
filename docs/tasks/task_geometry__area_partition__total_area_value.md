# `task_geometry__area_partition__total_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `area_partition`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `total_area_from_shaded_partition`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_area_partition_measurements, unknown_role=area_measure, formula_schema=shaded_unit_fraction_area_to_total_area, partition_rule=visible_fraction_partition_rule); scene=area_partition; scope=total_area_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/area_partition.py`
