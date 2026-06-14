# `task_geometry__composite_shape__composite_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `composite_shape`
5. Query id: `rectangle_minus_triangle_area`, `l_shape_area`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_composite_shape_measurements, unknown_role=area_measure, formula_schema=composite_area_decomposition, decomposition_rule=visible_component_decomposition_rule); scene=composite_shape; scope=composite_area_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `composite_shape`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/composite_shape.yaml`
- Task module: `trace/tasks/geometry/composite_shape/composite_area_value.py`
