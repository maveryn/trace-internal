# `task_puzzles__voxel_ladder__checkpoint_reachability`

## Contract
1. Domain: `puzzles`
2. Scene id: `voxel_ladder`
3. Source implementation domain/group: `puzzles/topology`
4. Query id: sampled from `unreachable_checkpoint_label`, `reachable_checkpoint_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.topology.voxel_ladder_maze.PuzzlesTopologyVoxelLadderCheckpointReachabilityTask`
2. Prompt lookup domain/group: `puzzles/topology`
3. Prompt bundle: `puzzles_topology_v0`
4. Scene variants: `clean_isometric_voxels`, `worksheet_voxel_maze`, `game_board_voxel_maze`
5. The scene shows an isometric cube maze with a blue `START` cube, a red `GOAL` cube, colored checkpoint cubes, and black ladders between height levels.
6. The task asks either for the only unreachable checkpoint color name or for the count of checkpoint cubes reachable from `START`.
7. `answer_gt.type`: `string` for `unreachable_checkpoint_label`, `integer` for `reachable_checkpoint_count`
8. `evidence_gt.type`: `bbox_set` over the unreachable checkpoint cube or all reachable checkpoint cubes.
9. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
10. Answers and evidence are produced from the same metadata execution trace.
