# `task_geometry__pythagorean_dissection__pythagorean_square_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `pythagorean_dissection`
3. Scene id: `pythagorean_dissection`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `central_square_area_from_triangle_legs`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_pythagorean_dissection_measurements, unknown_role=area_measure, formula_schema=central_square_area_from_triangle_legs); scene=pythagorean_dissection; scope=pythagorean_square_area_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `pythagorean_dissection`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/pythagorean_dissection.yaml`
- Task module: `trace/tasks/geometry/pythagorean_dissection/pythagorean_square_area_value.py`
