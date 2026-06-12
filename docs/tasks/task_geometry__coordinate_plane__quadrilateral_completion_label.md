# `task_geometry__coordinate_plane__quadrilateral_completion_label`

## Contract
1. Domain: `geometry`
2. Scene id: `coordinate_plane`
3. Scene id: `coordinate_plane`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `parallelogram_completion_label`, `rectangle_completion_label`, `rhombus_completion_label`, `square_completion_label`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_candidate_point(candidate_points, quadrilateral_completion_rule=quadrilateral_type)); scene=coordinate_plane; scope=quadrilateral_completion_label`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `coordinate_plane`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate_plane.yaml`
- Task module: `trace/tasks/geometry/coordinate_plane/quadrilateral_completion_label.py`
