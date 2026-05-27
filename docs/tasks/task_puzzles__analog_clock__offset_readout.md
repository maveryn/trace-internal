# `task_puzzles__analog_clock__offset_readout`

## Identity
1. Domain: `puzzles`
2. Scene id: `analog_clock`
3. Source task group: `clock`
4. Task id: `task_puzzles__analog_clock__offset_readout`

## Contract
1. Objective: apply a minute offset to the time shown on one analog clock.
2. Branch metadata: `query_id`
3. `query_id`: `minutes_after` or `minutes_before`
4. Answer type: `string` in strict `HH:MM` format.
5. Evidence type: `bbox_set` with hour-hand and minute-hand bboxes.
6. Query knobs: `offset_unit=minutes` and `offset_direction=after|before`.

## Prompt + Trace
1. Prompt bundle: `puzzles_clock_v0`
2. Scene key: `analog_clock`
3. Task key: `clock_readout_query`
4. Internal prompt variant key: `offset_time`
5. Trace records the shown time, offset unit, offset direction, delta value, answer time, hand geometry, style axes, and support ranges.
6. Generation is deterministic from `instance_seed`; answers and evidence come from the finalized clock geometry.
