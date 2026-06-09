# `task_geometry__coordinate_plane__segment_relation_count`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `parallel_count`, `perpendicular_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
- `count(filter(coordinate_plane_segment_pairs, segment_relation(pair)=target_segment_relation)); scene=coordinate_plane; scope=segment_relation_count`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Task module: `trace/tasks/geometry/coordinate/relation.py`
