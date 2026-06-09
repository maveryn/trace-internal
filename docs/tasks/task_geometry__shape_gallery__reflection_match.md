# `task_geometry__shape_gallery__reflection_match`

## Contract
1. Domain: `geometry`
2. Task group: `transformation`
3. Scene id: `shape_gallery`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `reflection_match`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_option(candidate_shapes, transform_rule=reflection_match)); scene=shape_gallery; scope=reflection_match`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/transformation.yaml`
- Task module: `trace/tasks/geometry/transformation/match.py`
