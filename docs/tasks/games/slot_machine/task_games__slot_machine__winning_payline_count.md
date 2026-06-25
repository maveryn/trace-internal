# `task_games__slot_machine__winning_payline_count`

## Contract
1. Domain: `games`
2. Scene: `slot_machine`
3. Scene id: `slot_machine`
4. Public task id: `task_games__slot_machine__winning_payline_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer`
7. Annotation schema: `segment_set`

## Program Contract
`count(payline for payline in rows_plus_long_diagonals if all_symbols_match(payline)); scene=slot_machine; scope=winning_payline_count`

## Generation Notes
1. The scene renders a front-view toy slot machine with a 3x3 visible reel window.
2. Paylines are the three full rows plus the two long diagonals; columns are not paylines.
3. A payline wins only when all three visible symbols on that row or diagonal match.
4. The answer is balanced across `0..5` winning paylines by construction.
5. Annotation is an unordered segment set, one centerline segment for each winning payline.
6. Scalar annotation checked: true.
