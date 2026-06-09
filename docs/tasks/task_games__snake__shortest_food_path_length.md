# `task_games__snake__shortest_food_path_length`

## Contract
1. Domain: `games`
2. Task group: `snake`
3. Scene id: `snake`
4. Public task id: `task_games__snake__shortest_food_path_length`
5. Supported `query_id` values: `shortest_food_path_length`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `length(shortest_path(head, food, blocked=current_body_or_wall)); scene=snake; scope=shortest_food_path_length`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is a set of cells on one shortest safe path from the head to the food, excluding the head cell and including the food cell.
4. The path treats current snake body cells and gray wall cells as fixed blockers.
