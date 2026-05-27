# `task_puzzles__voxel_cube__cube_painted_face_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_painted_face_count`
4. Objective: answer painted-face counting questions for a solid cube structure.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `painted_face_count`
3. Supported query parameter: `painted_query=exterior_face_total|exact_k_faces_cube_count`
4. Supported `scene_variant` values: `stack_strip`, `stack_card`, `stack_outline`
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `bbox_set`
7. Scene contract:
   - the scene shows one solid wall-like cube stack,
   - no structure contains floating cubes,
   - each structure uses either one row or one column,
   - painted exterior scenes use height `2` with `3..5` cubes,
   - every exterior unit-cube face is painted, including bottom faces.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant key: `painted_exterior_face_count` or `exact_k_painted_faces_cube_count`
5. Prompt-facing answers are exact integer counts.

## 4) Evidence + Trace Contract
1. Evidence is exactly one bbox for the visible cube structure.
2. `execution_trace.internal_query_id` records the selected painted-face query.
3. Exterior painted-face counts per cube, height grids, cube coordinate records, cube color, answer support, and supporting structure ids are recorded.
4. Prompt-facing evidence is projected from structure ids, not inferred from pixels.
