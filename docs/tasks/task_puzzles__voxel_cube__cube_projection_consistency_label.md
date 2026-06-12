# `task_puzzles__voxel_cube__cube_projection_consistency_label`

## 1) Identity
1. Domain: `puzzles`
2. Scene: `spatial`
3. Task id: `task_puzzles__voxel_cube__cube_projection_consistency_label`
4. Objective: select the labeled projection or cube-stack option that resolves a cube-stack projection consistency question.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `projection_consistency_label`
3. Public `scene_id`: `voxel_cube`
4. Supported internal query parameter: `consistency_query=inconsistent_projection_label|candidate_stack_from_views_label`
5. `answer_gt.type`: `string`
6. `annotation_gt.type`: `bbox_set`
7. Scene contract:
   - inconsistent-projection queries show one isometric cube stack and five labeled projection panels, each with a view title,
   - stack-from-views queries show three projection panels and labeled candidate cube stacks,
   - exactly one labeled option is correct.

## 3) Prompt Contract
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Internal prompt variant keys: `inconsistent_projection_label|candidate_stack_from_views_label`
5. Prompt-facing answers are option letters.

## 4) Annotation + Trace Contract
1. Annotation contains one bbox for the selected labeled option panel.
2. `execution_trace.consistency_query` records the internal query branch.
3. Stack footprint/heights, projection cells, option panels, and the correct option label are recorded.
4. Prompt-facing annotation is projected from the selected option panel, not inferred from pixels.
