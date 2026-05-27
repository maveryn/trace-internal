# task_games__minecraft__tunnel_clearance_count

1. Domain: `games`
2. Task group: `minecraft`
3. Scene id: `minecraft`
4. Query id: `tunnel_clearance_count`
5. Objective: count solid blocks that must be mined from a marked tunnel path.

The image renders a Minecraft-like isometric block world with a highlighted tunnel path, a player marker, and solid blocks both on and off the marked path.

The answer is an integer: the number of solid blocks sitting on the marked tunnel path. Empty marked cells and off-path distractor blocks do not count.

Evidence is `bbox_set`: one bounding box for each solid block on the marked tunnel path.

Generation samples grid size, visual style, bent tunnel path, path-block positions, and distractor blocks. The answer support is `2..6`, with balanced answer sampling by default.
