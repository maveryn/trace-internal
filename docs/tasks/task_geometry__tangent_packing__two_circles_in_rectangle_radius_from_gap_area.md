# `task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `tangent_packing`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `two_circles_in_rectangle_radius_from_gap_area`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `difference(value(two_circles_in_rectangle_radius_from_gap_area_source_a), value(two_circles_in_rectangle_radius_from_gap_area_source_b), mode=absolute); scene=tangent_packing; scope=two_circles_in_rectangle_radius_from_gap_area`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/circle_square_tangent_packing.py`
