# `task_games__minecraft__resource_route_cost`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__resource_route_cost`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_set`

## Program Contract
`sum(values(route_blocks, metric=resource_cost)); scene=minecraft; scope=resource_route_cost`

## Generation Notes
1. The scene shows labeled colored routes across an isometric block world.
2. For the named route only, each raised stone or dirt block on that route costs 1.
3. Empty route cells and blocks on other routes do not count.
4. Annotation points mark the centers of the counted raised blocks on the queried route.
