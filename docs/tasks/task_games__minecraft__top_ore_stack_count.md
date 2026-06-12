# `task_games__minecraft__top_ore_stack_count`

## Contract
1. Domain: `games`
2. Scene id: `minecraft`
3. Public task id: `task_games__minecraft__top_ore_stack_count`
4. Supported `query_id` values: `top_ore_stack_count`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(stacks, top_block_type=target_ore_type)); scene=minecraft; scope=top_ore_stack_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
4. Annotation points mark the center of the top cube of each counted stack.
