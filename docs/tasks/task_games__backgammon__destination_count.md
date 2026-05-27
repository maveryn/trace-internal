# `task_games__backgammon__destination_count`

## Contract
1. Domain: `games`
2. Scene id: `backgammon`
3. Source task group: `backgammon`
4. Query ids: `legal_move_count`, `hit_move_count`, `blocked_destination_count`
5. Objective: Count Backgammon destination points matching the sampled condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over qualifying destination points.
3. Public `query_variant` is `default`; the sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_backgammon_v0`
2. The generator samples the three destination-count query ids inside one public task.
