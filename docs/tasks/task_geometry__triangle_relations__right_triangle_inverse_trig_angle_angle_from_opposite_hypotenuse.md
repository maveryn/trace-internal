# `task_geometry__triangle_relations__right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
3. Scene id: `triangle_relations`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `angle_from_opposite_hypotenuse`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_triangle_relations_measurements, unknown_role=angle_measure, formula_schema=inverse_sin_opposite_hypotenuse); scene=triangle_relations; scope=right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse.py`
