# `task_puzzles__nonogram__nonogram_line_completion_label`

## Summary
1. Domain: `puzzles`
2. Scene: `logic`
3. Task id: `task_puzzles__nonogram__nonogram_line_completion_label`
4. Scene id: `nonogram`
5. Goal: choose the row-strip option that satisfies the marked nonogram row clue and the visible partial cells.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `line_completion_label`
3. Grid size: `6x6..9x9`
4. Option count: `4..6`
5. Answer type: `option_letter`
6. Annotation type: `bbox_set`
7. Annotation target: marked row clue box, marked row box, and selected option panel box
8. Scene variants: `nonogram_classic|nonogram_card|nonogram_blueprint`
