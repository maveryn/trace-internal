# `task_games__cards__missing_card_to_complete_hand_label`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__missing_card_to_complete_hand_label`
4. Supported `query_id` values: `missing_flush_card_label`, `missing_straight_card_label`, `missing_full_house_card_label`, `missing_three_of_kind_card_label`
5. Answer schema: `string_label`
6. Annotation schema: `bbox_set`
7. Program schema: `label(select(candidate_cards, completes_pattern(partial_hand, candidate_card, target_pattern))); scene=cards; scope=missing_card_to_complete_hand_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal pattern branches inside the same public task contract.
3. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
4. Annotation is the selected candidate-card bbox projected from the same generated card state used for answer verification.
