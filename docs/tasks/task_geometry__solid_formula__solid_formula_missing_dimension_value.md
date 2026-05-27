# `task_geometry__solid_formula__solid_formula_missing_dimension_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_formula`
4. Public query id: `default`
5. Query ids: `cylinder_cone_radius_from_volume_heights`, `cylinder_cone_height_from_volume_radius`, `prism_pyramid_height_from_volume`, `house_prism_length_from_volume`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_solid_formula_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute one missing solid dimension from visible formula labels on a compound solid. Variants include shared radius or cylinder height for a stacked cylinder-plus-cone solid, prism height for a rectangular prism with a pyramid cap, and length for a house-shaped compound prism. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the unknown-dimension label followed by the visible volume label and the supporting dimension labels needed for the computation. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_formula.py`
