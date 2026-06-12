# `task_geometry__concentric_chord__chord_length_from_radii`

## Contract
1. Domain: `geometry`
2. Scene id: `concentric_chord`
3. Scene id: `concentric_chord`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `chord_length_from_radii`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_concentric_chord_measurements, unknown_role=length_measure, formula_schema=chord_length_from_radii); scene=concentric_chord; scope=chord_length_from_radii`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `concentric_chord`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/concentric_chord.yaml`
- Task module: `trace/tasks/geometry/concentric_chord/chord_length_from_radii.py`
