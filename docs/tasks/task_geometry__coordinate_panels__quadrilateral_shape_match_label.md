# `task_geometry__coordinate_panels__quadrilateral_shape_match_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_panels`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `parallelogram_shape_match_label`, `rectangle_shape_match_label`, `rhombus_shape_match_label`, `square_shape_match_label`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox_set`

## Program Contract
- `label(select_panel(candidate_coordinate_panels, quadrilateral_type)); scene=coordinate_panels; scope=quadrilateral_shape_match_label`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Task module: `trace/tasks/geometry/coordinate/quadrilateral.py`
