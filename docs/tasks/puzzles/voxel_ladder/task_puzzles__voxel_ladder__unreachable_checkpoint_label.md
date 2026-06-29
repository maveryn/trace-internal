# `task_puzzles__voxel_ladder__unreachable_checkpoint_label`

## Program Contract
1. Program code: `select(checkpoint_color, predicate=unreachable_from_start); scene=voxel_ladder; scope=colored_checkpoints`.
2. The scene renders an isometric voxel maze with `START`, `GOAL`, colored checkpoint cubes, and black ladders.
3. Legal movement uses adjacent same-height cube tops and black ladders for height changes.
4. The task asks for the color name of the single checkpoint cube unreachable from `START`.
5. Query id: `single`.
6. Answer binding: color name of the unique unreachable checkpoint.
7. Annotation binding: scalar bbox around the unreachable checkpoint cube.
8. `scalar_annotation_checked = true`.

## Output Contract
1. `answer_gt.type = string`.
2. `annotation_gt.type = bbox`.
3. Annotation schema: scalar `bbox`.
4. Prompt bundle: `puzzles_voxel_ladder_v1`.
5. Source: `trace/tasks/puzzles/voxel_ladder/unreachable_checkpoint_label.py`.

## Trace Notes
1. `execution_trace` records movement graph, checkpoint metadata, and unreachable checkpoint color.
2. The generator constructs exactly one unreachable checkpoint for this task.
