# `task_games__darts__condition_count`

## Contract
1. Domain: `games`
2. Scene id: `darts`
3. Source task group: `darts`
4. Query ids: `ring_count`, `threshold_score_count`
5. Objective: Count darts matching the sampled scoring condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over qualifying dart markers.
3. Public `query_variant` is `default`; the sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_darts_v0`
2. Total-score option selection remains a separate task.
