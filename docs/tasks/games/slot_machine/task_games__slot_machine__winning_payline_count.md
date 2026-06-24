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
`count(row for row in horizontal_slot_paylines if all_symbols_match(row)); scene=slot_machine; scope=winning_payline_count`

## Generation Notes
1. The scene renders a front-view toy slot machine with five reels and three horizontal paylines.
2. A payline wins only when all five visible symbols on that row match.
3. The answer is balanced across `0..3` winning paylines by construction.
4. Annotation is an unordered segment set, one centerline segment for each winning payline.
5. Scalar annotation checked: true.
