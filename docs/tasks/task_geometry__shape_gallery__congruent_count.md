# `task_geometry__shape_gallery__congruent_count`

## Contract
1. Domain: `geometry`
2. Task group: `similarity`
3. Scene id: `shape_gallery`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `congruent_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
- `count(filter(candidate_shapes, shape_relation(shape, reference_shape)=congruent_to_reference)); scene=shape_gallery; scope=congruent_count`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/similarity.yaml`
- Task module: `trace/tasks/geometry/similarity/count.py`
