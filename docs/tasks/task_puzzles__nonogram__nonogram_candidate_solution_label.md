# `task_puzzles__nonogram__nonogram_candidate_solution_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__nonogram__nonogram_candidate_solution_label`
4. Scene id: `nonogram`
5. Goal: choose the filled-grid candidate that satisfies all visible row and column nonogram clues.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `candidate_solution_label`
3. Grid size: `6x6..9x9`
4. Option count: `4..6`
5. Answer type: `option_letter`
6. Evidence type: `bbox_set`
7. Evidence target: row-clue rail box, column-clue rail box, and selected candidate option panel box
8. Scene variants: `nonogram_classic|nonogram_card|nonogram_blueprint`
