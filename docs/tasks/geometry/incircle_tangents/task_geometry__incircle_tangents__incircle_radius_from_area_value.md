# `task_geometry__incircle_tangents__incircle_radius_from_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `incircle_tangents`
5. Query id: `inradius_from_area_and_tangent_segments`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_incircle_tangents_measurements, unknown_role=radius_length, formula_schema=inradius_from_area_and_tangent_segments); scene=incircle_tangents; scope=incircle_radius_from_area_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `incircle_tangents`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/incircle_tangents.yaml`
- Task module: `trace/tasks/geometry/incircle_tangents/incircle_radius_from_area_value.py`
