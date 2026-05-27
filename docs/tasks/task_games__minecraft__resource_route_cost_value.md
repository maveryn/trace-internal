# task_games__minecraft__resource_route_cost_value

1. Domain: `games`
2. Task group: `minecraft`
3. Scene id: `minecraft`
4. Query id: `resource_route_cost`
5. Objective: count the block cost along one named labeled mining route.

The image renders a Minecraft-like isometric block world with several labeled colored routes. The prompt names one route label to evaluate.

The answer is an integer: the cost of the named route only. Each raised stone or dirt block sitting on that route costs 1, and empty route cells cost 0. Other routes do not count.

Evidence is `bbox_set`: the raised stone or dirt blocks on the named route only. If the named route has cost zero, the evidence set is empty.

Generation samples queried route label, two route labels, route costs, route-block positions, grid size, and visual style. The answer support is `0..5`, with balanced answer sampling by default.
