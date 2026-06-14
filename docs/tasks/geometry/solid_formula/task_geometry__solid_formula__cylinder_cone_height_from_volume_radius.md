# `task_geometry__solid_formula__cylinder_cone_height_from_volume_radius`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_formula`
5. Query id: `cylinder_cone_height_from_volume_radius`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_solid_formula_measurements, unknown_role=radius_length, formula_schema=cylinder_cone_height_from_volume_radius); scene=solid_formula; scope=cylinder_cone_height_from_volume_radius`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `solid_formula`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_formula.yaml`
- Task module: `trace/tasks/geometry/solid_formula/cylinder_cone_height_from_volume_radius.py`
