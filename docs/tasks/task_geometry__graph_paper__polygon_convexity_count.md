# `task_geometry__graph_paper__polygon_convexity_count`

## Contract
1. Domain: `geometry`
2. Task group: `counting`
3. Scene id: `graph_paper`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `polygon_convexity_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
- `count(filter(graph_paper_polygons, polygon_convexity(shape)=target_convexity_class)); scene=graph_paper; scope=polygon_convexity_count`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/counting.yaml`
- Task module: `trace/tasks/geometry/counting/value.py`
