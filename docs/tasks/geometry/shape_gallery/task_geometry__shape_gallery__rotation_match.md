# `task_geometry__shape_gallery__rotation_match`

## Contract
1. Domain: `geometry`
2. Scene id: `shape_gallery`
5. Query id: `single`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_option(candidate_shapes, transform_rule=rotation_match)); scene=shape_gallery; scope=rotation_match`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `shape_gallery`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a `point_set` containing the winning polygon's visible vertices in pixel coordinates. The reference polygon, transformation cue, graph coordinates, labels, and construction metadata remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/shape_gallery.yaml`
- Task module: `trace/tasks/geometry/shape_gallery/rotation_match.py`
