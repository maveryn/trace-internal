# `task_puzzles__voxel_ladder__reachable_checkpoint_count`

## Program Contract
1. Program code: `count(checkpoint_cube, predicate=reachable_from_start); scene=voxel_ladder; scope=colored_checkpoints`.
2. The scene renders an isometric voxel maze with `START`, `GOAL`, colored checkpoint cubes, and black ladders.
3. Legal movement uses adjacent same-height cube tops and black ladders for height changes.
4. The task asks how many colored checkpoint cubes are reachable from `START`.
5. Query id: `single`.
6. Answer binding: reachable checkpoint count.
7. Annotation binding: bbox set over all reachable checkpoint cubes.
8. `scalar_annotation_checked = true`; scalar annotation is not used because the answer cardinality is variable.

## Output Contract
1. `answer_gt.type = integer`.
2. `annotation_gt.type = bbox_set`.
3. Annotation schema: unordered `bbox_set`.
4. Prompt bundle: `puzzles_voxel_ladder_v1`.
5. Source: `trace/tasks/puzzles/voxel_ladder/reachable_checkpoint_count.py`.

## Trace Notes
1. `execution_trace` records the movement graph, checkpoint metadata, and reachable count.
2. The generated answer range is configured as 2..5 unless task params override it.
