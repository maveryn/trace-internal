# `task_games__sokoban__shortest_path_sequence_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Source implementation domain/group: `games/sokoban`
4. Task id: `task_games__sokoban__shortest_path_sequence_label`
5. Objective contract: shortest path sequence label.
6. Supported sampled `query_id`: `shortest_path_sequence_label`
7. `answer_gt.type`: `option_letter`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.games.sokoban.shortest_path_sequence_label.GamesSokobanShortestPathSequenceLabelTask`
2. Prompt lookup domain/group: `games/sokoban`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `cool_room`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
