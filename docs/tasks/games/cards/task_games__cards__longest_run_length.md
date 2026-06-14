# `task_games__cards__longest_run_length`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Public task id: `task_games__cards__longest_run_length`
4. Supported `query_id` values: `default`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_set`
7. Program schema: `max(lengths(consecutive_rank_runs(cards_in_display_order))); scene=cards; scope=longest_run_length`

## Program Contract
- `max(lengths(consecutive_rank_runs(cards_in_display_order))); scene=cards; scope=longest_run_length`

## Generation Notes
2. Prompt wording comes from `prompts/games/cards/games_cards_v1.json`.
3. Annotation is projected from the same generated game state used for answer verification.
