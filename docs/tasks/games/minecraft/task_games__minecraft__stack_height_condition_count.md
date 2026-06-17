# `task_games__minecraft__stack_height_condition_count`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__stack_height_condition_count`
4. Supported `query_id` values: `exact_height_count`, `at_least_height_count`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Program Contract
`count(filter(stacks, height_relation(stack.height, target_height)=exact|at_least)); scene=minecraft; scope=stack_height_condition_count`

## Generation Notes
1. The scene contains visible cube columns with contiguous block levels from the ground upward.
2. `exact_height_count` asks for stacks exactly the target height.
3. `at_least_height_count` asks for stacks at least the target height.
4. Annotation boxes enclose every qualifying visible stack.
5. The generated answer support is capped at 5.
