# `task_puzzles__voxel_cube__cube_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `voxel_cube`
3. Source scene package: `voxel_cube`
4. Task id: `task_puzzles__voxel_cube__cube_count`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks for the total number of unit cubes in one visible isometric voxel structure.
3. Internal variation: stack dimensions, cube count, scene treatment, palette, and font/render style are generation/render metadata.

## Program Contract
`count(unit_cubes(stack)); scene=voxel_cube; scope=cube_count`

1. Program code: `voxel_cube.unit_cube_count`
2. Scene: `voxel_cube`
3. Scope: `cube_count`
4. Candidate set: every unit cube encoded by the sampled height grid.
5. Answer binding: integer unit-cube count.
6. Annotation binding: one image-pixel `bbox` around the voxel structure.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `annotation_gt.type = bbox`
3. Annotation schema: scalar `bbox`
4. Annotation target: the full rendered voxel structure.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_voxel_cube_v1`
2. Scene key: `voxel_cube`
3. Task key: `cube_count_query`
4. Query key: `cube_count`
