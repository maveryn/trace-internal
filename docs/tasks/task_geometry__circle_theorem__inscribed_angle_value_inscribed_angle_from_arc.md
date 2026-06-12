# `task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_arc`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_theorem`
3. Scene id: `circle_theorem`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `inscribed_angle_from_arc`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_circle_theorem_measurements, derivation_rule=inscribed_angle_from_arc, output_role=angle_measure); scene=circle_theorem; scope=inscribed_angle_value_inscribed_angle_from_arc`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `circle_theorem`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_theorem.yaml`
- Task module: `trace/tasks/geometry/circle_theorem/inscribed_angle_value_inscribed_angle_from_arc.py`
