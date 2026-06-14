# `task_games__cards__poker_draw_card_label`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__poker_draw_card_label`
4. Supported `query_id` values: `default`
5. Answer schema: `string_label`
6. Annotation schema: `bbox_set`
7. Program schema: `label(arg_extreme(candidate_cards, metric=poker_hand_rank(partial_hand + candidate_card), direction=best)); scene=cards; scope=poker_draw_card_label`

## Program Contract
- `label(arg_extreme(candidate_cards, metric=poker_hand_rank(partial_hand + candidate_card), direction=best)); scene=cards; scope=poker_draw_card_label`

## Generation Notes
2. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
3. Annotation is the selected candidate-card bbox projected from the same generated card state used for answer verification.
