# `task_games__space_shooter__highest_threat_label`

## Contract
1. Domain: `games`
2. Scene id: `space_shooter`
3. Source task group: `space_shooter`
4. Query id: `highest_threat_label`
5. Objective: Identify the labeled enemy ship closest to the bottom player baseline.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: bbox_set with one box around the selected enemy ship.
3. Public `query_variant` is `default`; `highest_threat_label` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Space-shooter playfield renderer.
2. Prompt bundle: `games_space_shooter_v0`
3. The sampled scene has a unique lowest enemy ship by construction.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, enemy count, unique threat placement, and visual style remain explicit params inside the task.
