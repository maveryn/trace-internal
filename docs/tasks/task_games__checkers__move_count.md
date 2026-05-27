# `task_games__checkers__move_count`

## Contract
1. Domain: `games`
2. Scene id: `checkers`
3. Source task group: `checkers`
4. Query ids: `legal_move_count`, `capture_move_count`
5. Objective: Count Checkers landing squares matching the sampled move condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over qualifying landing squares.
3. Public `query_variant` is `default`; the sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_checkers_v0`
2. Longest capture-chain reasoning remains a separate task.
