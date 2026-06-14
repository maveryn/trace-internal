# `task_geometry__sector__angle_from_sector_measure_angle_from_arc_length_and_radius`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
5. Query id: `angle_from_arc_length_and_radius`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_sector_measurements, derivation_rule=angle_from_arc_length_and_radius, output_role=angle_measure); scene=sector; scope=angle_from_sector_measure_angle_from_arc_length_and_radius`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `sector`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Task module: `trace/tasks/geometry/sector/angle_from_sector_measure_angle_from_arc_length_and_radius.py`
