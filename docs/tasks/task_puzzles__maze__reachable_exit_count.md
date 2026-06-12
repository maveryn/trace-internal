# `task_puzzles__maze__reachable_exit_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `maze`
3. Scene: `topology`
4. Task id: `task_puzzles__maze__reachable_exit_count`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `reachable_exit_count`
3. Prompts ask for the number of labeled boundary exits reachable from `START`.
4. Supported `scene_variant` values are `classic_wall_maze|paper_labyrinth_maze|block_wall_maze`.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the reachable-exit count.
3. `annotation_gt.type = bbox_set`
4. Annotation contains one bbox for each reachable exit label and doorway.

## Trace Contract
1. `execution_trace` records maze dimensions, start cell, open edges, exits, reachable labels, answer value, supporting item ids, and solver trace.
2. `render_map.item_bboxes_px` stores exit label+doorway bboxes keyed by item id.
3. `render_spec.scene_style.maze` records resolved wall/floor/marker palette, stroke, and marker-shape choices.
4. `render_spec.text_style.font` records the global vendored font used for START and exit labels.
5. Annotation is projected from recorded exit ids, not inferred from pixels.

## Prompt Contract
1. Bundle: `puzzles_topology_v0`
2. Scene key: `topology_maze_exit_puzzle`
3. Task key: `maze_exit_label_query`
4. Query key: `reachable_exit_count`
