# `task_puzzles__voxel_cube__cube_projection_match_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `voxel_cube`
3. Source scene package: `voxel_cube`
4. Task id: `task_puzzles__voxel_cube__cube_projection_match_label`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks which labeled projection option matches the selected view of the voxel structure.
3. Internal variation: selected `view_direction`, option count, and correct option label are trace metadata.

## Program Contract
`select_label(projection_options, option = orthographic_projection(stack, view_direction)); scene=voxel_cube; scope=cube_projection_match_label`

1. Program code: `voxel_cube.projection_option_match`
2. Scene: `voxel_cube`
3. Scope: `cube_projection_match_label`
4. Candidate set: visible projection option panels labeled `A`..`D`.
5. Answer binding: selected option letter.
6. Annotation binding: one image-pixel `bbox` around the selected projection option panel.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `annotation_gt.type = bbox`
3. Annotation schema: scalar `bbox`
4. Annotation target: the correct projection option panel.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_voxel_cube_v1`
2. Scene key: `voxel_cube`
3. Task key: `cube_projection_match_label_query`
4. Query key: `projection_match_label`
