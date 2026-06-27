# `task_geometry__angle_relations__parallel_algebraic_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `angle_relations`
4. Query ids: `target_angle_value`, `variable_x_value`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`

## Program Contract
- `derive_geometry_metric(visible_parallel_line_angle_expressions, derivation_rule=parallel_transversal_algebra, output_role=target_angle_measure|variable_x); scene=angle_relations; scope=parallel_algebraic_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `angle_relations`.
- Prompt schema: external prompt bundle
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. The annotation is a keyed point map over exactly the labeled transversal points `P`, `Q`, and `R`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/angle_relations.yaml`
- Task module: `trace/tasks/geometry/angle_relations/parallel_algebraic_angle_value.py`
