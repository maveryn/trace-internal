# `task_games__pool__pottable_ball_count`

## Contract
1. Domain: `games`
2. Scene id: `pool`
3. Source task group: `pool`
4. Query ids: `pottable_ball_count`, `legal_group_pottable_count`
5. Objective: Count pottable balls matching the sampled direct-shot condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over qualifying object balls.
3. Public `query_variant` is `default`; the sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_pool_v0`
2. Blocking-ball lane reasoning remains a separate task.
