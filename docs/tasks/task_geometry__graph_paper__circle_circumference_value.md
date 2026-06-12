# `task_geometry__graph_paper__circle_circumference_value`

## Contract
1. Domain: `geometry`
2. Scene id: `graph_paper`
3. Scene id: `graph_paper`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `perimeter`
6. Answer schema: `symbolic_expression`
7. Annotation schema: `point_set`

## Program Contract
- `solve_formula(visible_graph_paper_measurements, unknown_role=perimeter_measure, formula_schema=perimeter); scene=graph_paper; scope=circle_circumference_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `graph_paper`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/graph_paper.yaml`
- Task module: `trace/tasks/geometry/graph_paper/circle_circumference_value.py`
