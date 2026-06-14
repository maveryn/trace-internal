# `task_games__minecraft__stack_height_condition_count`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__stack_height_condition_count`
4. Supported `query_id` values: `exact_height_count`, `at_least_height_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(stack for stack in visible_cube_stacks if height_condition(stack.height, target_height)); scene=minecraft; scope=stack_height_condition_count`

## Generation Notes
1. The scene contains visible cube columns with contiguous block levels from the ground upward.
2. Target heights are sampled from `2..5` for exact-height queries and `2..4` for at-least-height queries.
3. The answer range is `1..6`.
4. Annotation points mark the center of the top cube of each qualifying visible stack.
