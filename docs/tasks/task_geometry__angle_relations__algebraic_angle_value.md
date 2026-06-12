# `task_geometry__angle_relations__algebraic_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `angle_relations`
3. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
4. Query ids: `triangle_single_extension_expression`, `triangle_double_extension_expression`
5. Answer schema: `integer_value`
6. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_angle_relations_measurements, derivation_rule=algebraic_triangle_extension_expression, output_role=angle_measure); scene=angle_relations; scope=algebraic_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `angle_relations`.
- Prompt schema: `v1`
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. The annotation is a keyed point map over exactly `ABC`, `BAC`, and `BCD`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/angle_relations.yaml`
- Task module: `trace/tasks/geometry/angle_relations/algebraic_angle_value.py`
