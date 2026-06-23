# `task_games__solitaire__same_suit_run_length_value`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__same_suit_run_length_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `length(same_suit_descending_run_from_marked_card); scene=solitaire; scope=same_suit_run_length_value`
8. Scalar annotation checked: `true`

## Program Contract
- `length(same_suit_descending_run_from_marked_card); scene=solitaire; scope=same_suit_run_length_value`

## Generation Notes
1. The marked card is the first card in the counted run.
2. The run follows cards downward in the same tableau column, same suit, decreasing by one rank each step.
3. Annotation contains one bbox for every card in the counted run, including the marked card.
4. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
