# `task_puzzles__voxel_cube__cube_visible_projection_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_visible_projection_count`
4. Objective: count filled cells in an orthographic projection of a cube stack.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `visible_cube_count`
3. Supported query parameter: `view_direction=top|front|right`
4. Supported `scene_variant`: `cube_stack`
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `bbox_set`
7. Scene contract:
   - the scene shows an isometric cube stack on the left and one blank orthographic query grid on the right,
   - `Front view` means looking at the left vertical face of the drawn stack,
   - `Right view` means looking at the right vertical face of the drawn stack,
   - the answer is the number of query-grid cells filled by the requested view.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant key: `visible_cube_count`
5. Prompt-facing answers are exact integer counts.

## 4) Evidence + Trace Contract
1. Evidence contains one bbox for each query-grid cell that should be filled.
2. `execution_trace.internal_query_id` records the selected view query.
3. Stack footprint/heights, visible counts for `top|front|right`, projection-cell coordinates, and query-panel geometry are recorded.
4. Prompt-facing evidence is projected from projection cells, not inferred from pixels.
