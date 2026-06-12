# `task_games__cards__higher_than_reference_count`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__higher_than_reference_count`
4. Supported `query_id` values: `default`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(cards, compare(rank(card), rank(reference_card), direction=greater_than))); scene=cards; scope=higher_than_reference_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
3. Annotation is projected from the same generated game state used for answer verification.
