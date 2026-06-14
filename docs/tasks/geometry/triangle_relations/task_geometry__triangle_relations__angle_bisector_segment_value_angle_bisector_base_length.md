# `task_geometry__triangle_relations__angle_bisector_segment_value_angle_bisector_base_length`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
5. Query id: `angle_bisector_base_length`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_triangle_relations_measurements, derivation_rule=angle_bisector_base_length, output_role=length_measure); scene=triangle_relations; scope=angle_bisector_segment_value_angle_bisector_base_length`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/angle_bisector_segment_value_angle_bisector_base_length.py`
