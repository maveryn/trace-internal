# `task_games__minecraft__resource_route_cost`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__resource_route_cost`
4. Supported `query_id` values: `resource_route_cost`
5. Answer schema: `integer_value`
6. Annotation schema: `point_set`
7. Program schema: `sum(values(route_blocks, metric=resource_cost)); scene=minecraft; scope=resource_route_cost`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
4. Annotation points mark the center of each counted raised stone or dirt block on the queried route.
