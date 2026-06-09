# `task_geometry__container_volume_transfer__target_capacity_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `container_volume_transfer`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `target_capacity_from_source_and_count`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_source_target_container_transfer, unknown_role=target_capacity, formula_schema=container_volume_transfer_target_capacity); scene=container_volume_transfer; scope=target_capacity_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_container_volume_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_container_bbox`, `target_container_bbox`, `source_dimension_region_bbox`, `transfer_count_bbox`, and `transfer_arrow_bbox`. Target dimensions are not shown for this task; the target capacity is derived from the source container volume and displayed full-pour count.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/container_volume_transfer.py`
