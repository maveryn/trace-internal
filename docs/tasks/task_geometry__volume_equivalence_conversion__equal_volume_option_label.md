# `task_geometry__volume_equivalence_conversion__equal_volume_option_label`

## Contract
1. Domain: `geometry`
2. Scene id: `volume_equivalence_conversion`
3. Scene id: `volume_equivalence_conversion`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `cone_matches_cylinder_option`, `cylinder_matches_cone_option`, `cuboid_matches_cylinder_option`
6. Answer schema: `option_letter`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `select_option(equal_volume_solid_conversion_options, target=option_with_matching_volume); scene=volume_equivalence_conversion`

## Prompt Bundle
- Prompt text is loaded from `geometry_volume_equivalence_conversion_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_solid_bbox`, `source_dimension_region_bbox`, `selected_option_bbox`, and `selected_option_dimension_region_bbox`. The option label is part of the answer, but annotation grounds the selected visual option and its dimensions. The visual answer options are labeled `A` through `E`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/volume_equivalence_conversion.yaml`
- Task module: `trace/tasks/geometry/volume_equivalence_conversion/equal_volume_option_label.py`
