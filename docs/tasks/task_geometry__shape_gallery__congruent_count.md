# `task_geometry__shape_gallery__congruent_count`

## Contract
1. Domain: `geometry`
2. Scene id: `shape_gallery`
3. Scene id: `shape_gallery`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `congruent_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
- `count(filter(candidate_shapes, shape_relation(shape, reference_shape)=congruent_to_reference)); scene=shape_gallery; scope=congruent_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `shape_gallery`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the unordered `bbox_set` around candidate shapes congruent to the reference shape. If the answer is `0`, annotation is an empty array. The reference shape, transform parameters, labels, and symbolic shape metadata remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/shape_gallery.yaml`
- Task module: `trace/tasks/geometry/shape_gallery/congruent_count.py`
