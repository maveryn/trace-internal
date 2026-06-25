# `task_games__slot_machine__paytable_score_value`

## Contract
1. Domain: `games`
2. Scene: `slot_machine`
3. Scene id: `slot_machine`
4. Public task id: `task_games__slot_machine__paytable_score_value`
5. Supported `query_id` values: `single`
6. Answer schema: `integer`
7. Annotation schema: `segment_set`

## Program Contract
`sum(paytable[matching_symbol(payline)] for payline in rows_plus_long_diagonals if all_symbols_match(payline)); scene=slot_machine; scope=paytable_score_value`

## Generation Notes
1. The scene renders a front-view toy slot machine with a 3x3 visible reel window and a side paytable.
2. Paylines are the three full rows plus the two long diagonals; columns are not paylines.
3. A payline scores only when all three visible symbols on that row or diagonal match.
4. The score for a winning payline is the side-paytable value for the matching symbol.
5. The answer is the integer sum over all winning paylines.
6. Generation samples one or two scoring paylines to keep the score-reading task compact.
7. Annotation is an unordered segment set, one centerline segment for each scoring payline.
8. Scalar annotation checked: true.
