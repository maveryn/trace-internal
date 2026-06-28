# `task_geometry__parallel_segment_proportion__variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `parallel_segment_proportion`
3. Task id: `task_geometry__parallel_segment_proportion__variable_value`
4. Query id: `single`
5. Answer schema: `number`
6. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_parallel_segment_proportion_triangle_points, unknown_role=variable_value, formula_schema=parallel_segment_ratio, output=number); scene=parallel_segment_proportion; scope=variable_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_parallel_segment_proportion_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` containing exactly the keys `A`, `B`, `C`, `D`, and `E`.
Each value is the pixel point for that visible construction point.

The construction family is internal replay metadata, not a public query id:

- `triangle_side_splitter`

Expression labels, parallel marks, segment geometry, and solved variable values remain visible diagram annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/parallel_segment_proportion.yaml`
- Task module: `trace/tasks/geometry/parallel_segment_proportion/variable_value.py`
