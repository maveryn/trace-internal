# `task_puzzles__voxel_cube__cube_visible_projection_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `voxel_cube`
3. Source scene package: `voxel_cube`
4. Task id: `task_puzzles__voxel_cube__cube_visible_projection_count`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks for how many cells are filled in a selected top/front/right orthographic projection.
3. Internal variation: selected `view_direction` is trace metadata and a prompt slot.

## Program Contract
`count(filled_cells(orthographic_projection(stack, view_direction))); scene=voxel_cube; scope=cube_visible_projection_count`

1. Program code: `voxel_cube.orthographic_projection_count`
2. Scene: `voxel_cube`
3. Scope: `cube_visible_projection_count`
4. Candidate set: cells in the rendered target projection grid.
5. Answer binding: integer count of projection cells filled by at least one cube.
6. Annotation binding: a `bbox_set` for all target projection cells that should be filled.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `annotation_gt.type = bbox_set`
3. Annotation schema: unordered `bbox_set`
4. Annotation target: all filled cells in the target projection grid.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_voxel_cube_v1`
2. Scene key: `voxel_cube`
3. Task key: `cube_visible_projection_count_query`
4. Query key: `visible_projection_count`
