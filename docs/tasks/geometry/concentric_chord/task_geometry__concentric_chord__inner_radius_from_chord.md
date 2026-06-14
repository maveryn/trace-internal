# `task_geometry__concentric_chord__inner_radius_from_chord`

## Contract
1. Domain: `geometry`
2. Scene id: `concentric_chord`
5. Query id: `inner_radius_from_chord`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_concentric_chord_measurements, unknown_role=radius_length, formula_schema=inner_radius_from_chord); scene=concentric_chord; scope=inner_radius_from_chord`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `concentric_chord`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/concentric_chord.yaml`
- Task module: `trace/tasks/geometry/concentric_chord/inner_radius_from_chord.py`
