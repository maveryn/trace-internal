# `task_puzzles__voxel_cube__cube_structure_change_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_structure_change_count`
4. Objective: count the cube delta between two related isometric cube structures.

## 2) Scene + Task Contract
1. Public `query_variant`: `default`
2. `query_id`: `cube_structure_change_count`
3. Supported query parameter: `change_type=missing_to_complete|removed`
4. Supported `scene_variant` values: `stack_strip`, `stack_card`, `stack_outline`
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `bbox_set`
7. Scene contract:
   - the scene shows two same-view wall-like cube structures with shared scale,
   - no structure contains floating cubes,
   - each structure uses either one row or one column, with length capped at 6,
   - active missing/removed answer counts are `1..6`,
   - completion and removal deltas are sampled on readable edge columns.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant key: `missing_to_complete_cuboid_count` or `removed_cube_count`
5. Prompt-facing answers are exact integer counts.

## 4) Evidence + Trace Contract
1. Evidence is exactly two bboxes for the left and right structures.
2. `execution_trace.internal_query_variant` records the selected change query.
3. Height grids, cube coordinate records, missing/removed cube coordinates, cube color, answer support, and supporting structure ids are recorded.
4. Prompt-facing evidence is projected from structure ids, not inferred from pixels.
