# `task_puzzles__voxel_ladder__unreachable_checkpoint_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `voxel_ladder`
3. Source implementation domain/group: `puzzles/topology`
4. Task id: `task_puzzles__voxel_ladder__unreachable_checkpoint_label`
5. Objective contract: unreachable checkpoint label.
6. Supported sampled `query_id`: `unreachable_checkpoint_label`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.topology.voxel_ladder_maze.PuzzlesTopologyVoxelLadderUnreachableCheckpointLabelTask`
2. Prompt lookup domain/group: `puzzles/topology`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `worksheet_voxel_maze`

## Notes
1. This task doc was refreshed during taxonomy-v0 puzzle migration from a retired broader public task id.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.
