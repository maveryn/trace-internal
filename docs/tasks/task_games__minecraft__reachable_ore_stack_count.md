# `task_games__minecraft__reachable_ore_stack_count`

## Contract
1. Domain: `games`
2. Task group: `minecraft`
3. Scene id: `minecraft`
4. Public task id: `task_games__minecraft__reachable_ore_stack_count`
5. Supported `query_id` values: `reachable_ore_stack_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(reachable_prefix(stack_line, step_rule=next_height<=current_height+1), top_block_type=target_ore_type)); scene=minecraft; scope=reachable_ore_stack_count`

## Generation Notes
1. The scene shows one highlighted isometric stack line ordered left to right.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
4. The leftmost stack is the start and is always the ground-level one-cube stack. Heights are nondecreasing; the reachable prefix stops before the first next stack that is 2 or more cubes taller.
5. Annotation points mark the center of the top cube of each counted reachable stack.
