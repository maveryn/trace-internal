# `task_geometry__function_graph__average_rate_value`

## Contract
1. Domain: `geometry`
2. Scene id: `function_graph`
5. Query id: `average_rate_between_marked_points`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `point_set`

## Program Contract
- `summary_statistic(values(visible_function_graph_support), statistic_schema=average_rate_between_marked_points); scene=function_graph; scope=average_rate_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `function_graph`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/function_graph.yaml`
- Task module: `trace/tasks/geometry/function_graph/average_rate_value.py`
