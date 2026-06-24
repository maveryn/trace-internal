# `task_geometry__shape_gallery__similar_count`

## Contract
1. Domain: `geometry`
2. Scene id: `shape_gallery`
5. Query id: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
- `count(filter(candidate_shapes, shape_relation(shape, reference_shape)=similar_to_reference)); scene=shape_gallery; scope=similar_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `shape_gallery`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is the unordered `bbox_set` around candidate shapes similar to the reference shape. If the answer is `0`, annotation is an empty array. The reference shape, scale/transform parameters, labels, and symbolic shape metadata remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/shape_gallery.yaml`
- Task module: `trace/tasks/geometry/shape_gallery/similar_count.py`
