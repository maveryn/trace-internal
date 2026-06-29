# `task_puzzles__voxel_ladder__checkpoint_sequence_label`

## Program Contract
1. Program code: `select(route_sequence_option, criterion=shortest_start_goal_checkpoint_color_sequence); scene=voxel_ladder; scope=route_sequence_options`.
2. The scene renders an isometric voxel maze with `START`, `GOAL`, colored checkpoint cubes, and black ladders.
3. Legal movement uses adjacent same-height cube tops and black ladders for height changes.
4. The task asks which rendered option card matches the checkpoint color sequence on the shortest valid route from `START` to `GOAL`.
5. Query id: `single`.
6. Answer binding: selected option letter.
7. Annotation binding: scalar bbox around the selected route-sequence option panel.
8. `scalar_annotation_checked = true`.

## Output Contract
1. `answer_gt.type = option_letter`.
2. `annotation_gt.type = bbox`.
3. Annotation schema: scalar `bbox`.
4. Prompt bundle: `puzzles_voxel_ladder_v1`.
5. Source: `trace/tasks/puzzles/voxel_ladder/checkpoint_sequence_label.py`.

## Trace Notes
1. `execution_trace` records route nodes, ladders, checkpoint reachability, option specs, selected option, and route checkpoint sequence.
2. Route and ladder proof details remain trace metadata; the public annotation marks only the selected visual answer witness.
