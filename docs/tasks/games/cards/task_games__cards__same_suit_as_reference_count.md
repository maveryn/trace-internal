# `task_games__cards__same_suit_as_reference_count`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__same_suit_as_reference_count`
4. Supported `query_id` values: `default`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(cards, suit(card) = suit(reference_card))); scene=cards; scope=same_suit_as_reference_count`

## Generation Notes
2. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
3. Annotation is projected from the same generated game state used for answer verification.
