# `task_geometry__triangle_relations__parallel_segment_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_relations`
3. Query id: `single`
4. Answer schema: `number`
5. Annotation schema: `point_map`
6. Scalar annotation checked: true

## Program Contract
- `solve_formula(parallel_segment_ratio_variable, unknown_role=variable_value, formula_schema=triangle_side_splitter_expression_ratio); scene=triangle_relations; scope=parallel_segment_variable_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `triangle_relations`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the labeled construction points `A`, `B`, `C`, `D`, and `E`. Parallel marks, expression labels, and solved segment values remain visible diagram content plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_relations.yaml`
- Task module: `trace/tasks/geometry/triangle_relations/parallel_segment_variable_value.py`
