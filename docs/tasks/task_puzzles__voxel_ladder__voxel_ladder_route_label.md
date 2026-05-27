# `task_puzzles__voxel_ladder__voxel_ladder_route_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `voxel_ladder`
3. Source implementation domain/group: `puzzles/topology`
4. Query id: sampled from `checkpoint_sequence_label`, `unreachable_checkpoint_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.topology.voxel_ladder.PuzzlesTopologyVoxelLadderRouteLabelTask`
2. Prompt lookup domain/group: `puzzles/topology`
3. Prompt bundle: `puzzles_topology_v0`
4. Scene variants: `clean_isometric_voxels`, `worksheet_voxel_maze`, `game_board_voxel_maze`
5. The scene shows an isometric cube maze with a blue `START` cube, a red `GOAL` cube, colored checkpoint cubes, and black ladders between height levels.
6. The task asks for a label matching the checkpoint sequence on the shortest route, or the color-name label of the unreachable checkpoint cube.
7. `answer_gt.type`: `string`
8. `evidence_gt.type`: `bbox_set` over the route endpoints/checkpoints/ladders or the unreachable checkpoint cube.
9. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
10. Answers and evidence are produced from the same metadata execution trace.
