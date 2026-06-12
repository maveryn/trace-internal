# `task_symbolic__analog_clock__offset_readout`

## Identity
1. Domain: `symbolic`
2. Scene id: `analog_clock`
3. Source scene: `clock`
4. Task id: `task_symbolic__analog_clock__offset_readout`

## Contract
1. Objective: apply a minute or second offset to the time shown on one analog clock.
2. Branch metadata: `query_id`
3. Default `query_id`: `minutes_after` or `minutes_before`; seconds aliases are supported when `offset_unit=seconds`.
4. Answer type: `string` in strict `HH:MM` or `HH:MM:SS` format.
5. Annotation type: `keyed_point_map` with `clock_center`, `hour_hand_tip`, `minute_hand_tip`, and optional `second_hand_tip`.
6. Query knobs: `offset_unit=minutes|seconds` and `offset_direction=after|before`.

## Prompt + Trace
1. Prompt bundle: `symbolic_clock_v0`
2. Scene key: `analog_clock`
3. Task key: `clock_readout_query`
4. Internal prompt variant key: `offset_time`
5. Trace records the shown time, offset unit, offset direction, delta value, answer time, hand geometry, style axes, and support ranges.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized clock geometry after font/style resolution.
