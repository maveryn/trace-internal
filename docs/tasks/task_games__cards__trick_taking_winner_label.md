# `task_games__cards__trick_taking_winner_label`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__trick_taking_winner_label`
4. Supported `query_id` values: `default`
5. Answer schema: `string_label`
6. Annotation schema: `bbox_set`
7. Program schema: `label(arg_extreme(played_cards, metric=trick_order_metric(card, lead_suit, trump_suit), direction=winning)); scene=cards; scope=trick_taking_winner_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
3. Annotation is projected from the same generated game state used for answer verification.
