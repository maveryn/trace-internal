# `task_games__sokoban__nearest_counterpart_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Source implementation domain/group: `games/sokoban`
4. Task id: `task_games__sokoban__nearest_counterpart_label`
5. Objective contract: nearest counterpart label.
6. Supported sampled `query_id`: `box_closest_to_marked_target_label`
7. `answer_gt.type`: `option_letter`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.games.sokoban.nearest_counterpart_label.GamesSokobanNearestCounterpartLabelTask`
2. Prompt lookup domain/group: `games/sokoban`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `paper_grid`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
