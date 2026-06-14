# `task_geometry__function_panels__intersection_property_label`

## Contract
1. Domain: `geometry`
2. Scene id: `function_panels`
5. Query id: `circle_circle_two_intersections_label`, `line_circle_tangent_label`, `line_circle_two_intersections_label`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox_set`

## Program Contract
- `label(select_panel(candidate_function_panels, primitive_pair_type, intersection_condition)); scene=function_panels; scope=intersection_property_label`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `function_panels`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/function_panels.yaml`
- Task module: `trace/tasks/geometry/function_panels/intersection_property_label.py`
