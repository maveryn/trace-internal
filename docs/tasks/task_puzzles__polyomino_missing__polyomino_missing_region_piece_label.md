# `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label`
4. Scene id: `polyomino_missing`
5. Goal: choose the piece that fills a missing region in a polyomino target or rectangular board.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `marked_region_piece_label` or `rectangle_complement_piece`
3. Rectangle-complement parameter: `matching_policy=exact_orientation|rotation_reflection_allowed`
4. Answer type: `option_letter`
5. Evidence type: `bbox_set`
6. Evidence targets: correct piece option panel bbox and missing-region bbox
7. Scene variants: `polyomino_strip|polyomino_card|polyomino_outline`
