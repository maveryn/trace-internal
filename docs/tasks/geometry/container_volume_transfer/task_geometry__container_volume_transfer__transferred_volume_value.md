# `task_geometry__container_volume_transfer__transferred_volume_value`

## Contract
1. Domain: `geometry`
2. Scene id: `container_volume_transfer`
5. Query ids: `repeated_cone_pours_total_volume`, `repeated_cylinder_pours_total_volume`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_map`

## Program Contract
- `solve_formula(visible_source_container_and_repeated_pours, target=total_transferred_volume, formula_schema=container_volume_transfer_transferred_volume); scene=container_volume_transfer; scope=transferred_volume_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_container_volume_transfer_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `source_container_bbox` and `target_container_bbox`. Numeric dimensions, transfer arrows, and pour-count labels remain visible in the image plus private verifier metadata, but are not requested as annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/container_volume_transfer.yaml`
- Task module: `trace/tasks/geometry/container_volume_transfer/transferred_volume_value.py`
