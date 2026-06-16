# `task_games__minecraft__top_ore_stack_count`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__top_ore_stack_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_set`

## Program Contract
`count(filter(stacks, top_block_type=target_ore_type)); scene=minecraft; scope=top_ore_stack_count`

## Generation Notes
1. The scene shows visible cube stacks in an isometric Minecraft-like block world.
2. The target ore type is sampled from gold ore or diamond ore.
3. The answer counts stacks whose top cube is the named ore, not ore blocks hidden below the top.
4. Annotation points mark the top-cube centers of every counted stack.
