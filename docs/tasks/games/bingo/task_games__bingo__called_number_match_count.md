# `task_games__bingo__called_number_match_count`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Public task id: `task_games__bingo__called_number_match_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(intersection(called_numbers, card_numbers)); scene=bingo; scope=called_number_match_count`

## Program Contract
- `count(intersection(called_numbers, card_numbers)); scene=bingo; scope=called_number_match_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the card-cell boxes whose printed numbers are present in the CALLED list.
