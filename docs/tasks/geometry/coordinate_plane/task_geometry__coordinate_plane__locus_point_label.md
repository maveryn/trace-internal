# `task_geometry__coordinate_plane__locus_point_label`

## Contract
1. Domain: `geometry`
2. Scene id: `coordinate_plane`
5. Query id: `annulus_region_point`, `circle_region_point`, `half_plane_intersection_region_point`, `vertical_strip_region_point`
6. Answer schema: `option_letter`
7. Annotation schema: `point_set`

## Program Contract
- `label(select_point(lettered_candidate_points, predicate=inside_shaded_region, region_rule_family)); scene=coordinate_plane; scope=locus_point_label`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `coordinate_plane`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/coordinate_plane.yaml`
- Task module: `trace/tasks/geometry/coordinate_plane/locus_point_label.py`
