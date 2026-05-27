# `task_games__bowling__first_pin_hit_label`

## Contract
1. Domain: `games`
2. Scene id: `bowling`
3. Source task group: `bowling`
4. Query id: `first_pin_hit_label`
5. Objective: Identify the labeled pin hit first by the visible ball trajectory.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: `bbox_set` over the selected pin.
3. `first_pin_hit_label` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games bowling-lane renderer.
2. Prompt bundle: `games_bowling_v0`
3. The displayed dashed arrow is a straight motion cue; generation verifies that the answer pin is the first physical pin intersected by the extrapolated ray.
4. First-hit construction also enforces a non-target ray-clearance margin so nearby visible pins are not plausible alternate first contacts.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Target label, visible pin count, style, haphazard pin placement, and visual layout remain explicit params inside the task.
