# `task_geometry__coordinate_plane__missing_endpoint_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `missing_endpoint_from_midpoint`, `missing_startpoint_from_midpoint`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_candidate_point(candidate_points, coordinate_rule=midpoint_inverse_endpoint, unknown_endpoint_role=endpoint_role)); scene=coordinate_plane; scope=missing_endpoint_label`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Task module: `trace/tasks/geometry/coordinate/algebra.py`
