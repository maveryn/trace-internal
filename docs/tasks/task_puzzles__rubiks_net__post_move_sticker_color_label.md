# `task_puzzles__rubiks_net__post_move_sticker_color_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `rubiks_net`
3. Source implementation domain/group: `puzzles/spatial`
4. Task id: `task_puzzles__rubiks_net__post_move_sticker_color_label`
5. Objective contract: post move sticker color label.
6. Supported sampled `query_id`: `one_move_sticker_color_label`
7. `answer_gt.type`: `option_letter`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.spatial.rubiks_cube.PuzzlesSpatialRubiksPostMoveStickerColorLabelTask`
2. Prompt lookup domain/group: `puzzles/spatial`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `classic_net`

## Notes
1. This task doc was refreshed during taxonomy-v0 puzzle migration from a retired broader public task id.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
