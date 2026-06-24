# `task_geometry__solid_formula__prism_pyramid_height_from_volume`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_formula`
3. Supported `query_id`: `single`
4. Answer schema: `decimal_value_1dp`
5. Annotation schema: `bbox_map`

## Program Contract
- `solve_formula(visible_solid_formula_measurements, unknown_role=prism_height, formula_schema=prism_pyramid_height_from_volume); scene=solid_formula; scope=prism_pyramid_height_from_volume`
- The image shows a rectangular prism with a pyramid cap. The prism height is unknown, while base length, base width, pyramid height, and volume are labeled.
- Annotation keys: `target_prism_height_label`, `volume_label`, `known_length_label`, `known_width_label`, `pyramid_height_label`.

## Prompt Bundle
- Prompt text is loaded from `geometry_solid_formula_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map witnesses for the visible measurement labels needed to solve the formula. Graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_formula.yaml`
- Task module: `trace/tasks/geometry/solid_formula/prism_pyramid_height_from_volume.py`
