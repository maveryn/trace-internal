# `task_puzzles__polyomino_missing__marked_region_piece_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `polyomino_missing`
3. Source implementation domain/group: `puzzles/spatial`
4. Task id: `task_puzzles__polyomino_missing__marked_region_piece_label`
5. Objective contract: marked region piece label.
6. Supported sampled `query_id`: `marked_region_piece_label`
7. `answer_gt.type`: `option_letter`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.spatial.polyomino_arrangement_label.PuzzlesSpatialPolyominoMarkedRegionPieceLabelTask`
2. Prompt lookup domain/group: `puzzles/spatial`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `polyomino_strip`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
