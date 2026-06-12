# `task_geometry__solid_revolution__revolution_frustum_volume_value`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_revolution`
3. Scene id: `solid_revolution`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `frustum_volume_from_trapezoid`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_solid_revolution_measurements, unknown_role=volume_measure, formula_schema=frustum_volume_from_trapezoid); scene=solid_revolution; scope=revolution_frustum_volume_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `solid_revolution`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_revolution.yaml`
- Task module: `trace/tasks/geometry/solid_revolution/revolution_frustum_volume_value.py`
