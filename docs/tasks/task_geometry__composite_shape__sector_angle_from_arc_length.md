# `task_geometry__composite_shape__sector_angle_from_arc_length`

## Contract
1. Domain: `geometry`
2. Scene id: `composite_shape`
3. Scene id: `composite_shape`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `sector_angle_from_arc_length`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_composite_shape_measurements, derivation_rule=sector_angle_from_arc_length, output_role=arc_length); scene=composite_shape; scope=sector_angle_from_arc_length`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `composite_shape`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/composite_shape.yaml`
- Task module: `trace/tasks/geometry/composite_shape/sector_angle_from_arc_length.py`
