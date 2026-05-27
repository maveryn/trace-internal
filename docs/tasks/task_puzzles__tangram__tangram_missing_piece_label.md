# `task_puzzles__tangram__tangram_missing_piece_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__tangram__tangram_missing_piece_label`
4. Scene id: `tangram`
5. Goal: choose the labeled candidate piece that matches a black missing region.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `missing_piece_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: correct option panel bbox followed by the black missing-region bbox
6. Scene variants: `tangram_square|tangram_diamond|tangram_tilted`
