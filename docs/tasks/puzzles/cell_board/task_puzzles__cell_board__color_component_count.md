# `task_puzzles__cell_board__color_component_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `cell_board`
3. Source implementation domain/group: `puzzles/cell_board`
4. Task id: `task_puzzles__cell_board__color_component_count`
5. Objective contract: color component count.
6. Supported sampled `query_id`: `color_components`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `point_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.cell_board.merged_tasks.TileColorComponentCountPublicTask`
2. Prompt lookup domain/group: `puzzles/cell_board`
3. Prompt bundle: `see trace prompt metadata`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
