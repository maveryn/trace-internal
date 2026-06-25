# `task_geometry__container_volume_transfer__resulting_height_value`

## Contract
1. Domain: `geometry`
2. Scene id: `container_volume_transfer`
5. Query ids: `cone_pours_to_cylinder_height`, `cylinder_pours_to_cuboid_height`
6. Answer schema: `number_value`
7. Annotation schema: `bbox_map`

## Program Contract
- `solve_formula(visible_source_target_container_transfer, unknown_role=resulting_liquid_height, formula_schema=container_volume_transfer_resulting_height); scene=container_volume_transfer; scope=resulting_height_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_container_volume_transfer_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_container_bbox` and `target_container_bbox`. Numeric dimensions, the visible pour-count label, and the fill mark remain visible in the image plus private verifier metadata; the target liquid-height value itself remains the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/container_volume_transfer.yaml`
- Task module: `trace/tasks/geometry/container_volume_transfer/resulting_height_value.py`
