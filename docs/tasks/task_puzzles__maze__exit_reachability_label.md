# `task_puzzles__maze__exit_reachability_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `maze`
3. Task group: `topology`
4. Task id: `task_puzzles__maze__exit_reachability_label`

## Query Contract
1. Public `query_variant`: `default`
2. `query_id`: `exit_reachability_label`
3. Prompts ask for one reachable or unreachable labeled boundary exit, controlled by `target_reachability`.
4. Supported `scene_variant` values are `classic_wall_maze|paper_labyrinth_maze|block_wall_maze`.

## Answer And Evidence
1. `answer_gt.type = string`
2. `answer_gt.value` is the requested exit label.
3. `evidence_gt.type = bbox_set`
4. Evidence contains one bbox for the target exit label and doorway.

## Trace Contract
1. `execution_trace` records maze dimensions, start cell, open edges, exits, reachable/unreachable labels, answer value, supporting item ids, and solver trace.
2. `render_map.item_bboxes_px` stores exit label+doorway bboxes keyed by item id.
3. Evidence is projected from recorded exit ids, not inferred from pixels.

## Prompt Contract
1. Bundle: `puzzles_topology_v0`
2. Scene key: `topology_maze_exit_puzzle`
3. Task key: `maze_exit_label_query`
4. Query key: `exit_reachability_label`
