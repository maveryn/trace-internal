# `task_geometry__function_graph__reference_line_crossing_count`

## Contract
1. Domain: `geometry`
2. Scene id: `function_graph`
5. Query id: `reference_line_crossing_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
- `count(intersections(visible_function_graph_primitives, crossing_rule=reference_line_crossing_count)); scene=function_graph; scope=reference_line_crossing_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `function_graph`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/function_graph.yaml`
- Task module: `trace/tasks/geometry/function_graph/reference_line_crossing_count.py`
