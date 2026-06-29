# `task_puzzles__overlay__overlay_result_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `overlay`
3. Objective: choose the labeled result option showing the union of two aligned transparent source sheets.
4. Answer type: `option_letter`
5. Annotation schema: `bbox`

## Program Contract
`select_label(transparent_overlay.option, rule=union_of_two_same_grid_source_sheets); scene=overlay; scope=overlay_result_label`

1. Candidate set: visual result option panels labeled `A` through `E` or `F`.
2. Selection rule: the selected option's marked cells equal the union of the left and right source-sheet marked cells.
3. Answer binding: selected option letter.
4. Annotation binding: one image-pixel `bbox` around the selected result option panel.

## Generation
1. Query id: `single`
2. Internal query metadata: `overlay_union_same_grid`
3. Grid size: `4x4..5x5`
4. Option count: `5..6`
5. Scene variants: `overlay_strip|overlay_card|overlay_outline`
6. Mark shapes: `circle|square|diamond|rounded_square`

## Review Notes
1. The annotation marks only the selected result option panel; the source sheets are context.
2. The correct option is unique by construction.
