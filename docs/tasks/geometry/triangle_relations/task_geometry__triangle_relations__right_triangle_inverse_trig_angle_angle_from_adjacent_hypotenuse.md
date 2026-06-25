# `task_geometry__triangle_relations__right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
5. Query id: `single`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `point`
8. Scalar annotation checked: true

## Program Contract
- `solve_formula(visible_triangle_relations_measurements, unknown_role=angle_measure, formula_schema=inverse_cos_adjacent_hypotenuse); scene=triangle_relations; scope=right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the target angle vertex as `[x,y]`. Graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse.py`
