# `task_puzzles__code_grid__decoded_word_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `code_grid`
3. Source implementation domain/group: `puzzles/word`
4. Task id: `task_puzzles__code_grid__decoded_word_label`
5. Objective contract: decoded word label.
6. Supported sampled `query_id`: `decode_coordinate_sequence`, `decode_spaced_coordinate_sequence`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `keyed_bbox_map`
9. Annotation policy: ordered role-bound cell witnesses with keys `cell_1`, `cell_2`, and so on.

## Implementation
1. Registered class: `trace.tasks.puzzles.word.code_grid.PuzzlesCodeGridDecodedWordLabelTask`
2. Prompt lookup domain/group: `puzzles/word`
3. Prompt bundle: `puzzles_word_v0`
4. Scene variants: `code_grid_classic`, `code_grid_notebook`, `code_grid_card`

## Notes
1. The scene displays row labels as uppercase letters and column labels as numbers.
2. The prompt supplies the coordinate sequence; the decoded answer is the ordered sequence of visible cell letters.
3. The generator avoids placing the decoded word elsewhere as a contiguous word-search-style hit.
