# `task_geometry__parallel_segment_proportion__segment_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `parallel_segment_proportion`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `triangle_side_splitter_segment_length` or `parallel_transversal_segment_length`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_parallel_segment_proportion_equation, unknown_role=target_segment_length, formula_schema=parallel_segment_ratio); scene=parallel_segment_proportion; scope=segment_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_geo3k_marked_equations_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of all proportional segment witnesses:

- `left_top_segment_start`
- `left_top_segment_end`
- `left_bottom_segment_start`
- `left_bottom_segment_end`
- `right_top_segment_start`
- `right_top_segment_end`
- `right_bottom_segment_start`
- `right_bottom_segment_end`

Expression labels, parallel marks, vertex labels, and solved variable values remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/geo3k_marked_equations.py`
