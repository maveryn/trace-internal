# `task_puzzles__voxel_cube__cube_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_count`
4. Objective: count all cubes in one visible isometric cube structure.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `cube_count`
3. Supported `scene_variant` values: `stack_strip`, `stack_card`, `stack_outline`
4. `answer_gt.type`: `integer`
5. `annotation_gt.type`: `bbox_set`
6. Scene contract:
   - the scene shows one solid wall-like cube stack,
   - no structure contains floating cubes,
   - each structure uses either one row or one column, with length capped at 6,
   - the active answer range is `8..12`,
   - cube color is sampled per instance from a non-semantic named-color support.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant key: `total_cube_count`
5. Prompt-facing answers are exact integer counts.

## 4) Annotation + Trace Contract
1. Annotation is exactly one bbox for the visible cube structure.
2. `execution_trace.internal_query_id = total_cube_count`.
3. Height grids, cube coordinate records, cube color, answer support, and supporting structure ids are recorded.
4. Prompt-facing annotation is projected from structure ids, not inferred from pixels.
