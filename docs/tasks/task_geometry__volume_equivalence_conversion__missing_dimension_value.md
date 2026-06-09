# `task_geometry__volume_equivalence_conversion__missing_dimension_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `volume_equivalence_conversion`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `cuboid_to_cylinder_length`, `cylinder_to_cone_height`, `cone_to_cuboid_height`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(equal_volume_solid_conversion, target=missing_dimension, formula_schema=volume_equivalence_missing_dimension); scene=volume_equivalence_conversion`

## Prompt Bundle
- Prompt text is loaded from `geometry_volume_equivalence_conversion_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_solid_bbox`, `target_solid_bbox`, `source_dimension_region_bbox`, `target_dimension_region_bbox`, and `target_unknown_region_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/volume_equivalence_conversion.py`
