# `task_puzzles__tents__tents_missing_tent_cell_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__tents__tents_missing_tent_cell_label`
4. Scene id: `tents`
5. Goal: choose the labeled cell that can contain the missing tent for the marked tree.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `missing_tent_cell_label`
3. Grid size: `6x6..8x8`
4. Candidate labels: `A..F`
5. Answer type: `option_letter`
6. Annotation type: `bbox_set`
7. Annotation target: selected candidate cell, marked tree, selected row clue, and selected column clue
8. Scene variants: `tents_classic|tents_card|tents_blueprint`
9. Render palettes: `garden|autumn|lake|violet|slate`
