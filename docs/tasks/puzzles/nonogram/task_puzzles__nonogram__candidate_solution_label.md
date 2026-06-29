# `task_puzzles__nonogram__candidate_solution_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `nonogram`
3. Objective: choose the labeled filled-grid option that satisfies all visible row and column clues.
4. Answer type: `option_letter`
5. Annotation schema: `bbox`

## Program Contract
`select_label(nonogram.option_grid, rule=all_row_and_column_clues_match); scene=nonogram; scope=filled_grid_satisfying_all_row_and_column_clues`

1. Program code: `selection.option_match`
2. Scene: `nonogram`
3. Scope: `filled_grid_satisfying_all_row_and_column_clues`
4. Candidate set: visual filled-grid option panels labeled `A`..`D` or `A`..`F`.
5. Selection rule: the selected grid must match every visible row clue and every visible column clue.
6. Answer binding: the selected option letter.
7. Annotation binding: one image-pixel `bbox` around the selected option panel.

## Generation
1. Query id: `single`
2. Grid size: `6x6..9x9`
3. Option count: `{4, 6}`
4. Scene variants: `nonogram_classic|nonogram_card|nonogram_blueprint`

## Review Notes
The annotation marks only the chosen visual option panel. The clue rails are question context, not answer witnesses.
