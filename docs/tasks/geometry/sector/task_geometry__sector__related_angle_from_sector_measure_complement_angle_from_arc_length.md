# `task_geometry__sector__related_angle_from_sector_measure_complement_angle_from_arc_length`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
5. Query id: `complement_angle_from_arc_length`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `derive_geometry_metric(visible_sector_measurements, derivation_rule=complement_angle_from_arc_length, output_role=arc_length); scene=sector; scope=related_angle_from_sector_measure_complement_angle_from_arc_length`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `sector`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Task module: `trace/tasks/geometry/sector/related_angle_from_sector_measure_complement_angle_from_arc_length.py`
