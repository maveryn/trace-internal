# `task_geometry__sector__related_angle_from_sector_measure_supplement_angle_from_area`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Scene id: `sector`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `supplement_angle_from_area`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_sector_measurements, derivation_rule=supplement_angle_from_area, output_role=area_measure); scene=sector; scope=related_angle_from_sector_measure_supplement_angle_from_area`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `sector`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Task module: `trace/tasks/geometry/sector/related_angle_from_sector_measure_supplement_angle_from_area.py`
