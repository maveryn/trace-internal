# `task_games__bowling__spare_path_label`

## Contract
1. Domain: `games`
2. Scene id: `bowling`
3. Source task group: `bowling`
4. Query id: `spare_path_label`
5. Objective: Choose the numbered aiming path whose straight extension passes through every remaining standing pin.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: `point_pair_set` over the selected visible dashed path cue.
3. `spare_path_label` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games bowling-lane renderer.
2. Prompt bundle: `games_bowling_v0`
3. Candidate paths are shown as shortened numbered dashed cues; the intended path is their straight extension toward the remaining standing pins.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Remaining pin count, path-option count, target path label, visible cue length, style, haphazard pin placement, and visual layout remain explicit params inside the task.
