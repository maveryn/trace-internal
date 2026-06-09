# `task_geometry__function_graph__extremum_count_turning_point_count`

## Contract
1. Domain: `geometry`
2. Task group: `graphing`
3. Scene id: `function_graph`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `turning_point_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
- `count(filter(function_graph_feature_points, feature_type=turning_point)); scene=function_graph; scope=extremum_count_turning_point_count`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/graphing.yaml`
- Task module: `trace/tasks/geometry/graphing/count.py`
