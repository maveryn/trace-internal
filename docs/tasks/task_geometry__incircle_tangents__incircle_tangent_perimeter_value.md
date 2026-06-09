# `task_geometry__incircle_tangents__incircle_tangent_perimeter_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `incircle_tangents`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `triangle_perimeter_from_tangent_segments`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_incircle_tangents_measurements, unknown_role=perimeter_measure, formula_schema=triangle_perimeter_from_tangent_segments); scene=incircle_tangents; scope=incircle_tangent_perimeter_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/tangent_polygon_incircle.py`
