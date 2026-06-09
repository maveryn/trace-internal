# `task_geometry__container_volume_transfer__fill_count_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `container_volume_transfer`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `cone_to_cylinder_fill_count`, `cylinder_to_cuboid_fill_count`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_source_target_container_transfer, unknown_role=full_pour_count, formula_schema=container_volume_transfer_fill_count); scene=container_volume_transfer; scope=fill_count_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_container_volume_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_container_bbox`, `target_container_bbox`, `source_dimension_region_bbox`, `target_dimension_region_bbox`, and `transfer_arrow_bbox`. Numeric dimension labels, unit labels, and the full-pours question mark remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/container_volume_transfer.py`
