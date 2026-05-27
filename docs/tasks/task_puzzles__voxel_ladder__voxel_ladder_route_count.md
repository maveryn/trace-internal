# `task_puzzles__voxel_ladder__voxel_ladder_route_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `voxel_ladder`
3. Source implementation domain/group: `puzzles/topology`
4. Query id: sampled from `reachable_checkpoint_count`, `shortest_ladder_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.topology.voxel_ladder.PuzzlesTopologyVoxelLadderRouteCountTask`
2. Prompt lookup domain/group: `puzzles/topology`
3. Prompt bundle: `puzzles_topology_v0`
4. Scene variants: `clean_isometric_voxels`, `worksheet_voxel_maze`, `game_board_voxel_maze`
5. The scene shows an isometric cube maze with a blue `START` cube, a red `GOAL` cube, colored checkpoint cubes, and black ladders between height levels.
6. The task counts reachable checkpoint cubes or ladders used on the shortest `START`-to-`GOAL` route.
7. `answer_gt.type`: `integer`
8. `evidence_gt.type`: `bbox_set` over reachable checkpoint cubes or shortest-route ladders.
9. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
10. Answers and evidence are produced from the same metadata execution trace.
