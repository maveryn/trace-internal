# `task_games__minecraft__resource_route_cost`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__resource_route_cost`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_set`

## Program Contract
`count(filter(track_cells, has_raised_stone_or_dirt_block=true)); scene=minecraft; scope=resource_route_cost`

## Generation Notes
1. The scene shows one visible track across an isometric block world.
2. Each raised stone or dirt block sitting on the track counts 1.
3. Empty track cells do not count.
4. Annotation points mark the centers of every counted raised block on the track.
