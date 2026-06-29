# `task_puzzles__voxel_cube__cube_painted_face_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `voxel_cube`
3. Source scene package: `voxel_cube`
4. Task id: `task_puzzles__voxel_cube__cube_painted_face_count`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks either for total painted exterior faces or for cubes with exactly a requested painted-face count.
3. Internal variation: `painted_query` and `exact_face_count` are trace metadata, not public task ids.

## Program Contract
`count(exterior_painted_faces(stack) or cubes_with_k_exterior_faces(stack, k)); scene=voxel_cube; scope=cube_painted_face_count`

1. Program code: `voxel_cube.exterior_surface_count`
2. Scene: `voxel_cube`
3. Scope: `cube_painted_face_count`
4. Candidate set: unit-cube exterior faces or unit cubes matching the requested exposed-face count.
5. Answer binding: integer count from the sampled voxel coordinates.
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
3. Task key: `cube_painted_face_count_query`
4. Query keys: `painted_exterior_face_count`, `exact_k_painted_faces_cube_count`
