# `task_games__minecraft__resource_route_cost`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__resource_route_cost`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Program Contract
`count(filter(track_cells, has_raised_stone_or_dirt_block=true)); scene=minecraft; scope=resource_route_cost`

## Generation Notes
1. The scene shows one visible track across an isometric block world.
2. Each raised stone or dirt block sitting on the track counts 1.
3. Empty track cells and raised blocks away from the track do not count.
4. Annotation boxes enclose every counted raised block on the track.
5. Counted raised blocks are never placed on the first or last track cell.
6. Off-track distractor blocks are sampled at least 3 grid cells away from the visible track.
