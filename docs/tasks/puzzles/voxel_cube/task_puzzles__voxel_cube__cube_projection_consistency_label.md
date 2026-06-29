# `task_puzzles__voxel_cube__cube_projection_consistency_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `voxel_cube`
3. Source scene package: `voxel_cube`
4. Task id: `task_puzzles__voxel_cube__cube_projection_consistency_label`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks which labeled projection panel is inconsistent with the shown voxel structure and its declared view direction.
3. Internal variation: declared option directions, option count, and inconsistent label are trace metadata.

## Program Contract
`select_label(projection_panels, panel not in valid_orthographic_projections(stack)); scene=voxel_cube; scope=cube_projection_consistency_label`

1. Program code: `voxel_cube.projection_consistency_check`
2. Scene: `voxel_cube`
3. Scope: `cube_projection_consistency_label`
4. Candidate set: visible projection option panels labeled `A`..`D`.
5. Answer binding: selected inconsistent option letter.
6. Annotation binding: one image-pixel `bbox` around the inconsistent projection panel.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `annotation_gt.type = bbox`
3. Annotation schema: scalar `bbox`
4. Annotation target: the inconsistent projection option panel.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_voxel_cube_v1`
2. Scene key: `voxel_cube`
3. Task key: `cube_projection_consistency_label_query`
4. Query key: `projection_consistency_label`
