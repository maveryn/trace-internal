# `task_geometry__triangle_relations__parallel_section_base_length`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
3. Scene id: `triangle_relations`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `parallel_section_base_length`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_triangle_relations_measurements, unknown_role=length_measure, formula_schema=parallel_section_base_length); scene=triangle_relations; scope=parallel_section_base_length`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/parallel_section_base_length.py`
