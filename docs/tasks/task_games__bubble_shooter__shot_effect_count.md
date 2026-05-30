# `task_games__bubble_shooter__shot_effect_count`

## Contract
1. Domain: `games`
2. Scene id: `bubble_shooter`
3. Source task group: `bubble_shooter`
4. Query ids: `pop_count`, `drop_count`
5. Objective: Count bubbles matching the sampled immediate shot-effect condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `point_set` over counted board-bubble centers.
3. The sampled shot-effect condition is retained as `query_id` and `query_spec.params.query_id` for diagnostics.

## Implementation
1. The scene shows a close-packed bubble-shooter board with a marked landing target and visible shot bubble.
2. `pop_count` counts existing board bubbles that pop, excluding the shot bubble.
3. `drop_count` counts bubbles that drop after the popped group is removed.
4. Prompt bundle: `games_bubble_shooter_v0`

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
