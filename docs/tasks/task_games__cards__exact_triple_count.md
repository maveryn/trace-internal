# `task_games__cards__exact_triple_count`

## Contract
1. Domain: `games`
2. Task group: `cards`
3. Scene id: `cards`
4. Public task id: `task_games__cards__exact_triple_count`
5. Supported `query_id` values: `exact_triple_count`
6. Answer schema: `integer_count`
7. Annotation schema: `keyed_bbox_set_map`
8. Program schema: `count(filter(ranks, count(cards_of_rank(rank)) = 3)); scene=cards; scope=exact_triple_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
