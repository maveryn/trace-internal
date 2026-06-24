# `task_geometry__split_triangle_trig_chain__side_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `split_triangle_trig_chain`
5. Supported `query_id`: `shared_altitude_two_angles_side`, `shared_altitude_side_then_hypotenuse`, or `isosceles_altitude_trig_side`
6. Answer schema: `number`
7. Annotation schema: `point_map`

## Program Contract
- `solve_formula(right_triangle_trig_chain, unknown_role=target_side_length, given_pattern=shared_altitude_two_angles_side|shared_altitude_side_then_hypotenuse|isosceles_altitude_trig_side); scene=split_triangle_trig_chain; scope=side_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_split_triangle_trig_chain_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the visible construction vertices:

- `A`
- `B`
- `C`
- `D`

This stays as `point_map`, not scalar `point`, because each valid instance requires multiple role-bound vertex witnesses. Numeric side labels, angle labels, right-angle markers, and equal-side ticks remain visible readouts plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/split_triangle_trig_chain.yaml`
- Task module: `trace/tasks/geometry/split_triangle_trig_chain/side_length_value.py`
