# `task_geometry__function_graph__reference_line_crossing_count`

## Contract
1. Domain: `geometry`
2. Scene id: `function_graph`
5. Query ids: `x_axis`, `horizontal_line`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
- `count(crossings(visible_function_graph_primitives, reference_line=x_axis|horizontal_line)); scene=function_graph; scope=reference_line_crossing_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `function_graph`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a pixel-space `point_set` containing every visible crossing point with the requested reference line. Graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/function_graph.yaml`
- Task module: `trace/tasks/geometry/function_graph/reference_line_crossing_count.py`
