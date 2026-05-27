# `task_games__snake__safe_direction_count`

## Contract
1. Domain: `games`
2. Task group: `snake`
3. Scene id: `snake`
4. Query id: `safe_direction_count`
5. Prompt bundle: `games_snake_v0`
6. Evidence type: `bbox_set`
7. Answer type: `integer`

## Query Notes
1. `safe_direction_count` asks how many of the four immediate directions are safe from the current snake head.
2. A safe move stays inside the board and avoids both the snake body and gray wall cells. Moving onto the red food is safe.
3. Evidence boxes mark the destination cells that are safe next moves.

## Generation Notes
The scene renders a visible Snake board with a yellow head, connected body cells, red food, and gray wall cells. The generator constructs a connected snake chain, samples wall cells away from the snake and food, and targets the requested safe-move count by construction before rendering.
