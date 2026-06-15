# `task_games__minecraft__reachable_ore_stack_count`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__reachable_ore_stack_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_set`

## Program Contract
`count(filter(reachable_prefix(stack_line, step_rule=next_height<=current_height+1), top_block_type=target_ore_type)); scene=minecraft; scope=reachable_ore_stack_count`

## Generation Notes
1. The scene shows one highlighted isometric stack line ordered left to right.
2. The leftmost stack is the start and is always a one-cube stack.
3. Heights are nondecreasing; the reachable prefix stops before the first next stack that is 2 or more cubes taller.
4. Annotation points mark the top-cube centers of every reachable counted stack.
