# `task_geometry__tangent_packing__circle_in_square_radius_from_gap_area`

## Contract
1. Domain: `geometry`
2. Scene id: `tangent_packing`
5. Query id: `circle_in_square_radius_from_gap_area`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `difference(value(circle_in_square_radius_from_gap_area_source_a), value(circle_in_square_radius_from_gap_area_source_b), mode=absolute); scene=tangent_packing; scope=circle_in_square_radius_from_gap_area`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `tangent_packing`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/tangent_packing.yaml`
- Task module: `trace/tasks/geometry/tangent_packing/circle_in_square_radius_from_gap_area.py`
