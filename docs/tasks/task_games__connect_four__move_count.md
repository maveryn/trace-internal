# `task_games__connect_four__move_count`

## Contract
1. Domain: `games`
2. Scene id: `connect_four`
3. Source task group: `connect_four`
4. Query ids: `winning_move_count`, `safe_move_count`
5. Objective: Count Connect Four drop columns matching the sampled move condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over qualifying drop landing cells.
3. The sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_connect_four_v0`
2. The generator samples immediate-winning and safe-drop count queries inside one public task.
