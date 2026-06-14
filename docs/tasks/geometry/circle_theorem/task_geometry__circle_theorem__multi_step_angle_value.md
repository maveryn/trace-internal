# `task_geometry__circle_theorem__multi_step_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_theorem`
5. Query id: `single`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_circle_theorem_measurements, derivation_rule=multi_step_angle_value, output_role=angle_measure); scene=circle_theorem; scope=multi_step_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `circle_theorem`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_theorem.yaml`
- Task module: `trace/tasks/geometry/circle_theorem/multi_step_angle_value.py`
