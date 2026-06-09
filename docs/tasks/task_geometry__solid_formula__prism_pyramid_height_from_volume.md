# `task_geometry__solid_formula__prism_pyramid_height_from_volume`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_formula`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `prism_pyramid_height_from_volume`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_solid_formula_measurements, unknown_role=height_length, formula_schema=prism_pyramid_height_from_volume); scene=solid_formula; scope=prism_pyramid_height_from_volume`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_formula.py`
