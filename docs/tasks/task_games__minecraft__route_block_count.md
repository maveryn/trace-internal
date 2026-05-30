# task_games__minecraft__route_block_count

1. Domain: `games`
2. Task group: `minecraft`
3. Scene id: `minecraft`
4. Query ids: `tunnel_clearance_count`, `resource_route_cost`
5. Objective: count solid blocks on a marked Minecraft-like path or named route.

The image renders a Minecraft-like isometric block world with either a highlighted tunnel path or labeled colored mining routes.

The answer is an integer. For `tunnel_clearance_count`, count the solid blocks sitting on the marked tunnel path. For `resource_route_cost`, count the raised stone or dirt blocks on the named route only.

Evidence is `bbox_set`: one bounding box for every counted cube block. For a named route with cost zero, the evidence set is empty.

Generation samples the internal query id, grid size, visual style, path or route geometry, path-block positions, distractor blocks or alternate routes, shared canvas treatment, font family, unit scale, and layout jitter. The answer support is `2..6` for tunnel clearance and `0..5` for route cost, with balanced answer sampling by default.
