# `task_geometry__sector__sector_area_value_area_from_arc_length_and_radius`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Scene id: `sector`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `area_from_arc_length_and_radius`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_sector_measurements, unknown_role=arc_length, formula_schema=area_from_arc_length_and_radius); scene=sector; scope=sector_area_value_area_from_arc_length_and_radius`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `sector`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Task module: `trace/tasks/geometry/sector/sector_area_value_area_from_arc_length_and_radius.py`
