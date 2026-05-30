# `task_games__darts__condition_count`

## Contract
1. Domain: `games`
2. Scene id: `darts`
3. Source task group: `darts`
4. Query ids: `ring_count`, `threshold_score_count`
5. Objective: Count darts matching the sampled scoring condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `point_set` over the centers of qualifying dart markers.
3. The sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_darts_v0`
2. Internal query ids are `ring_count` and `threshold_score_count`; both use the same integer answer and homogeneous dart-marker evidence contract.
3. Rendering uses the shared games/puzzles panel background layer, sampled text fonts, layout jitter, and six dartboard palette variants.
4. Total-score option selection remains a separate task.
