# `task_geometry__angle_relations__parallel_supplement_angle`

## Contract
1. Domain: `geometry`
2. Scene id: `angle_relations`
4. Query id: `parallel_supplement_angle`
5. Answer schema: `integer_value`
6. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_angle_relations_measurements, derivation_rule=parallel_supplement_angle, output_role=angle_measure); scene=angle_relations; scope=parallel_supplement_angle`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `angle_relations`.
- Prompt schema: external prompt bundle
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. The annotation is a keyed point map over exactly `CFE` and `AEF`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/angle_relations.yaml`
- Task module: `trace/tasks/geometry/angle_relations/parallel_supplement_angle.py`
