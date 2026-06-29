# `task_puzzles__maze__reachable_exit_count`

## Contract

1. Domain: `puzzles`
2. Scene package: `trace/tasks/puzzles/maze/`
3. Scene id: `maze`
4. Public task id: `task_puzzles__maze__reachable_exit_count`
5. Supported `query_id` values: `single`
6. Prompt query key: `reachable_exit_count`
7. Answer schema: `integer`
8. Annotation schema: `bbox_set`
9. Program schema: `count(maze.exit where reachable_from_start=true); scene=maze; scope=reachable_exit_count`

## Program Contract

- `count(maze.exit where reachable_from_start=true); scene=maze; scope=reachable_exit_count`

## Query Contract

- Supported public `query_id`: `single`
- The task counts all boundary exits connected to `START` through open corridors.
- Maze dimensions, exit count, target reachable count, scene treatment, font, marker shape, and theme are generation/render axes, not public taxonomy axes.

## Generation Contract

- The renderer shows one orthogonal wall maze with one `START` cell and labeled exits on the outer boundary.
- The reachable-exit answer is sampled within configured support and is unique by construction from the generated maze topology.
- Movement follows open corridors only; walls block motion.
- Supported visual variants are `classic_wall_maze`, `paper_labyrinth_maze`, and `block_wall_maze`.

## Prompt Contract

- Bundle: `puzzles_maze_v1`
- `scene_key`: `maze`
- `task_key`: `reachable_exit_count_query`
- `query_key`: `reachable_exit_count`
- Prompt-facing answer is the integer count of reachable exits.
- Prompt-facing annotation is a `bbox_set`, one image-pixel bbox per reachable exit marker and doorway.

## Annotation + Trace Contract

- `answer_gt.type`: `integer`
- `annotation_gt.type`: `bbox_set`
- `len(annotation_gt.value) == answer_gt.value`
- `projected_annotation` includes `bbox_set`, `pixel_bbox_set`, and `value`.
- `render_map.item_bboxes_px` stores exit bboxes keyed by exit item id.
- `execution_trace` records public query `single`, internal query `reachable_exit_count`, maze topology, reachable labels, answer count, and solver trace.
- Answer and annotation are projected from the same reachable exit item ids.
- `scalar_annotation_checked=true`.

## Determinism

- Deterministic sampling/rendering from `instance_seed`, scene config, prompt bundle, and code version.
- No semantic auto-relaxation is used to force acceptance.
