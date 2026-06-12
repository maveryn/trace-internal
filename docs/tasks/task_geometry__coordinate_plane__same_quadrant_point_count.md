# `task_geometry__coordinate_plane__same_quadrant_point_count`

## Contract
1. Domain: `geometry`
2. Scene id: `coordinate_plane`
3. Scene id: `coordinate_plane`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `same_quadrant_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
- `count(filter(points, quadrant(point)=quadrant(reference_point))); scene=coordinate_plane; scope=same_quadrant_point_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `coordinate_plane`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the unordered `point_set` of candidate point centers in the same quadrant as the reference point. If the answer is `0`, annotation is an empty array. Graph coordinates, labels, and construction metadata remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate_plane.yaml`
- Task module: `trace/tasks/geometry/coordinate_plane/same_quadrant_point_count.py`
