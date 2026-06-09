# `task_games__cards__trick_taking_winner_label`

## Contract
1. Domain: `games`
2. Task group: `cards`
3. Scene id: `cards`
4. Public task id: `task_games__cards__trick_taking_winner_label`
5. Supported `query_id` values: `trick_taking_winner_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(arg_extreme(played_cards, metric=trick_order_metric(card, lead_suit, trump_suit), direction=winning)); scene=cards; scope=trick_taking_winner_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
