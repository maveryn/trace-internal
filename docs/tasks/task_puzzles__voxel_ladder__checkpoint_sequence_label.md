# `task_puzzles__voxel_ladder__checkpoint_sequence_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `voxel_ladder`
3. Source implementation domain/group: `puzzles/topology`
4. Query id: `checkpoint_sequence_label`

## Implementation
1. Registered class: `trace.tasks.puzzles.topology.voxel_ladder_maze.PuzzlesTopologyVoxelLadderCheckpointSequenceLabelTask`
2. Prompt lookup domain/group: `puzzles/topology`
3. Prompt bundle: `puzzles_topology_v0`
4. Scene variants: `clean_isometric_voxels`, `worksheet_voxel_maze`, `game_board_voxel_maze`
5. The scene shows an isometric cube maze with a blue `START` cube, a red `GOAL` cube, colored checkpoint cubes, and black ladders between height levels.
6. The task asks for the option letter matching the checkpoint color sequence on the shortest route from `START` to `GOAL`.
7. `answer_gt.type`: `option_letter`
8. `evidence_gt.type`: `bbox_set` over the route endpoints, route checkpoint cubes, and route ladders.
9. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
10. Answers and evidence are produced from the same metadata execution trace.
