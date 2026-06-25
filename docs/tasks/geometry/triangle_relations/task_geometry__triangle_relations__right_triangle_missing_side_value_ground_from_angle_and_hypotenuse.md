# `task_geometry__triangle_relations__right_triangle_missing_side_value_ground_from_angle_and_hypotenuse`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
5. Query id: `single`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `segment`
8. Scalar annotation checked: true

## Program Contract
- `derive_geometry_metric(visible_triangle_relations_measurements, derivation_rule=ground_from_angle_and_hypotenuse, output_role=length_measure); scene=triangle_relations; scope=right_triangle_missing_side_value_ground_from_angle_and_hypotenuse`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the requested visual segment as `[[x0,y0],[x1,y1]]`. Graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/right_triangle_missing_side_value_ground_from_angle_and_hypotenuse.py`
