# `task_puzzles__nonogram__line_completion_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `nonogram`
3. Objective: choose the labeled row-strip option that completes the marked nonogram row.
4. Answer type: `option_letter`
5. Annotation schema: `bbox`

## Program Contract
`select_label(nonogram.row_strip, rule=row_clue_matches_and_visible_cells_match); scene=nonogram; scope=marked_row_strip_satisfying_row_clue_and_visible_cells`

1. Program code: `selection.option_match`
2. Scene: `nonogram`
3. Scope: `marked_row_strip_satisfying_row_clue_and_visible_cells`
4. Candidate set: visual row-strip option panels labeled `A`..`D` or `A`..`F`.
5. Selection rule: the selected strip must satisfy the marked row clue and match the visible cells in the marked row.
6. Answer binding: the selected option letter.
7. Annotation binding: one image-pixel `bbox` around the selected option panel.

## Generation
1. Query id: `single`
2. Grid size: `6x6..9x9`
3. Option count: `{4, 6}`
4. Scene variants: `nonogram_classic|nonogram_card|nonogram_blueprint`

## Review Notes
The annotation marks only the chosen visual option panel. The clue rail and marked row are question context, not answer witnesses.
