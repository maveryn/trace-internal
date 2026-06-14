# `task_puzzles__star_battle__valid_cell_anywhere_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `star_battle`
3. Source implementation domain/group: `puzzles/logic`
4. Task id: `task_puzzles__star_battle__valid_cell_anywhere_label`
5. Objective contract: valid cell anywhere label.
6. Supported sampled `query_id`: `valid_cell_anywhere_label`
7. `answer_gt.type`: `option_letter`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.star_battle_grid.PuzzlesLogicStarBattleValidCellAnywhereLabelTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `star_battle_classic`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
