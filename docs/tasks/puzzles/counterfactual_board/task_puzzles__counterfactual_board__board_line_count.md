# `task_puzzles__counterfactual_board__board_line_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `counterfactual_board`
3. Source implementation domain/group: `puzzles/counterfactual`
4. Task id: `task_puzzles__counterfactual_board__board_line_count`
5. Objective contract: board line count.
6. Supported sampled `query_id`: `vertical_line_count`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.counterfactual.board_grid_count.PuzzlesCounterfactualBoardLineCountTask`
2. Prompt lookup domain/group: `puzzles/counterfactual`
3. Prompt bundle: `see trace prompt metadata`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
