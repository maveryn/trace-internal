# `task_geometry__volume_equivalence_conversion__equal_volume_option_label`

## Contract
1. Domain: `geometry`
2. Scene id: `volume_equivalence_conversion`
3. Task id: `task_geometry__volume_equivalence_conversion__equal_volume_option_label`
4. Supported `query_id` values: `cone_matches_cylinder_option`, `cylinder_matches_cone_option`, `cuboid_matches_cylinder_option`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires source, selected-option, and dimension-region boxes)

## Program Contract
- `select_option(equal_volume_solid_conversion_options, target=option_with_matching_volume); scene=volume_equivalence_conversion; scope=equal_volume_option_label`

## Query Semantics
- `cone_matches_cylinder_option` asks which cylinder option has the same volume as the source cone.
- `cylinder_matches_cone_option` asks which cone option has the same volume as the source cylinder.
- `cuboid_matches_cylinder_option` asks which cylinder option has the same volume as the source cuboid.
- Option count, option order rotation, numeric conversion case, style, palette, and render retry index are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/volume_equivalence_conversion/geometry_volume_equivalence_conversion_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a pixel-space bbox map with `source_solid_bbox`, `source_dimension_region_bbox`, `selected_option_bbox`, and `selected_option_dimension_region_bbox`. The option label is the answer, while annotation grounds the selected visual option and its dimensions. Visual answer options are labeled `A` through `D` or `A` through `F`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/volume_equivalence_conversion.yaml`
- Prompt bundle: `prompts/geometry/volume_equivalence_conversion/geometry_volume_equivalence_conversion_v1.json`
- Task module: `trace/tasks/geometry/volume_equivalence_conversion/equal_volume_option_label.py`
