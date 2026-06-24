# `task_games__solitaire__column_card_count_value`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__column_card_count_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(visible_cards_in_requested_tableau_column); scene=solitaire; scope=column_card_count_value`
8. Scalar annotation checked: `true`

## Program Contract
- `count(visible_cards_in_requested_tableau_column); scene=solitaire; scope=column_card_count_value`

## Generation Notes
1. The prompt names a visible tableau column by its 1-based column number.
2. The answer is the number of visible cards in that column.
3. Annotation contains the bboxes for all visible cards in the requested column.
4. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
