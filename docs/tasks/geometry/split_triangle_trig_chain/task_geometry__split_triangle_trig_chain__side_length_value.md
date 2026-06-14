# `task_geometry__split_triangle_trig_chain__side_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `split_triangle_trig_chain`
5. Query id: `shared_altitude_two_angles_side`, `shared_altitude_side_then_hypotenuse`, or `isosceles_altitude_trig_side`
6. Answer schema: `number`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(split_triangle_trig_chain, unknown_role=target_side_length, formula_schema=right_triangle_trig_with_shared_altitude); scene=split_triangle_trig_chain; scope=side_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_split_triangle_patterns_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target segment, altitude, known segment, and angle witnesses:

- `target_segment_start`
- `target_segment_end`
- `altitude_start`
- `altitude_end`
- `known_segment_start`
- `known_segment_end`
- `known_angle` or `known_angle_left`
- optional `known_angle_right`

Numeric side labels, angle labels, right-angle markers, and equal-side ticks remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/split_triangle_trig_chain.yaml`
- Task module: `trace/tasks/geometry/split_triangle_trig_chain/side_length_value.py`
