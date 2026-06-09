# `task_puzzles__voxel_cube__cube_projection_match_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_projection_match_label`
4. Objective: select the orthographic projection option matching a cube stack from a requested view.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `projection_match_label`
3. Public `scene_id`: `voxel_cube`
4. Supported query parameter: `view_direction=top|front|right`
5. `answer_gt.type`: `string`
6. `annotation_gt.type`: `bbox_set`
7. Scene contract:
   - the scene shows one isometric cube stack and labeled projection-grid options,
   - `Front view` means looking at the left vertical face of the drawn stack,
   - `Right view` means looking at the right vertical face of the drawn stack,
   - exactly one labeled option matches the requested projection.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant key: `projection_match_label`
5. Prompt-facing answers are option letters.

## 4) Annotation + Trace Contract
1. Annotation contains one bbox for the selected projection option panel.
2. `execution_trace.internal_query_id` records the selected view query.
3. Stack footprint/heights, visible counts for `top|front|right`, candidate projection cells, and the correct option label are recorded.
4. Prompt-facing annotation is projected from the selected option panel, not inferred from pixels.
