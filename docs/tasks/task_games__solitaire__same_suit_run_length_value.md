# `task_games__solitaire__same_suit_run_length_value`

## Contract
1. Domain: `games`
2. Task group: `solitaire`
3. Scene id: `solitaire`
4. Public task id: `task_games__solitaire__same_suit_run_length_value`
5. Supported `query_id` values: `same_suit_descending_run_length`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `length(same_suit_descending_run_from_marked_card(tableau_column)); scene=solitaire; scope=same_suit_run_length_value`

## Generation Notes
1. The marked card is the first card in the counted run.
2. The run follows cards downward in the same tableau column.
3. Annotation contains one bbox for every card in the counted run, including the marked card.
