# `task_games__battleship__ship_status_count`

## Contract
1. Domain: `games`
2. Scene id: `battleship`
3. Source task group: `battleship`
4. Query ids: `sunk_ship_count`, `partial_ship_count`
5. Objective: Count fleet ships matching the sampled hit-status condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over cells belonging to qualifying ships.
3. The sampled condition is retained as `query_id`.

## Implementation
1. Prompt bundle: `games_battleship_v0`
2. The generator samples sunk-ship and partial-ship count queries inside one public task.
