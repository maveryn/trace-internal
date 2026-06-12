# `task_games__pacman__next_item_label`

## Contract
1. Domain: `games`
2. Scene id: `pacman`
3. Public task id: `task_games__pacman__next_item_label`
4. Supported `query_id` values: `next_item_label`
5. Answer schema: `string_label`
6. Annotation schema: `point_set`
7. Program schema: `label(first_item_on_route(route, items)); scene=pacman; scope=next_item_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
