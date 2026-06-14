# `task_geometry__graph_paper__quadrilateral_type_count`

## Contract
1. Domain: `geometry`
2. Scene id: `graph_paper`
5. Query id: `quadrilateral_type_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`

## Program Contract
- `count(filter(graph_paper_quadrilaterals, quadrilateral_type(shape)=target_quadrilateral_type)); scene=graph_paper; scope=quadrilateral_type_count`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `graph_paper`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/graph_paper.yaml`
- Task module: `trace/tasks/geometry/graph_paper/quadrilateral_type_count.py`
