# `task_geometry__circle_theorem__secant_secant_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `secant_secant_length`, `secant_secant_variable_segment_length`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_circle_theorem_measurements, unknown_role=length_measure, formula_schema=secant_secant_length); scene=circle_theorem; scope=secant_secant_length_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/theorem_value.py`
