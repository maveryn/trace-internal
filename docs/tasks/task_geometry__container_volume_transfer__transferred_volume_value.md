# `task_geometry__container_volume_transfer__transferred_volume_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `container_volume_transfer`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `repeated_cone_pours_total_volume`, `repeated_cylinder_pours_total_volume`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_source_container_and_repeated_pours, target=total_transferred_volume, formula_schema=container_volume_transfer_transferred_volume); scene=container_volume_transfer`

## Prompt Bundle
- Prompt text is loaded from `geometry_container_volume_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_container_bbox`, `target_container_bbox`, `source_dimension_region_bbox`, `transfer_count_bbox`, and `transfer_arrow_bbox`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/container_volume_transfer.py`
