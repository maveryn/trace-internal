# `task_geometry__solid_formula__cylinder_cone_height_from_volume_radius`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_formula`
3. Task id: `task_geometry__solid_formula__cylinder_cone_height_from_volume_radius`
4. Supported `query_id` values: `single`
5. Answer schema: `decimal_value_1dp`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires multiple role-bound boxes for the visible measurement labels)

## Program Contract
- `solve_formula(visible_solid_formula_measurements, unknown_role=cylinder_height, formula_schema=cylinder_cone_height_from_volume_radius); scene=solid_formula; scope=cylinder_cone_height_from_volume_radius`
- The image shows a cylinder with a cone on top. The cylinder height is unknown, while radius, cone height, and total volume are labeled.
- Annotation keys: `target_cylinder_height_label`, `volume_label`, `radius_label`, `cone_height_label`.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/solid_formula/geometry_solid_formula_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map witnesses for the visible measurement labels needed to solve the formula. Graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_formula.yaml`
- Prompt bundle: `prompts/geometry/solid_formula/geometry_solid_formula_v1.json`
- Task module: `trace/tasks/geometry/solid_formula/cylinder_cone_height_from_volume_radius.py`
