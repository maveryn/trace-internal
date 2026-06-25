# `task_games__slot_machine__reel_completion_label`

## Contract
1. Domain: `games`
2. Scene: `slot_machine`
3. Scene id: `slot_machine`
4. Public task id: `task_games__slot_machine__reel_completion_label`
5. Supported `query_id` values: `single`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox`

## Program Contract
`unique_label(option for option in third_reel_options if count(payline for payline in rows_plus_long_diagonals if all_symbols_match(first_two_reels + option)) == 1); scene=slot_machine; scope=reel_completion_label`

## Generation Notes
1. The scene renders the first two visible reels of a 3x3 slot machine and four labeled candidate third reels.
2. Paylines are the three full rows plus the two long diagonals; columns are not paylines.
3. Exactly one candidate third reel completes one matching-symbol payline.
4. The other three candidate third reels complete no paylines.
5. The answer is the selected option letter.
6. Annotation is the scalar bounding box around the selected third-reel option panel.
7. Scalar annotation checked: true.
