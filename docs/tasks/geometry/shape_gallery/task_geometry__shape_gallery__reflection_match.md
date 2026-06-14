# `task_geometry__shape_gallery__reflection_match`

## Contract
1. Domain: `geometry`
2. Scene id: `shape_gallery`
5. Query id: `reflection_match`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_option(candidate_shapes, transform_rule=reflection_match)); scene=shape_gallery; scope=reflection_match`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `shape_gallery`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/shape_gallery.yaml`
- Task module: `trace/tasks/geometry/shape_gallery/reflection_match.py`
