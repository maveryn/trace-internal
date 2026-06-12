# `task_puzzles__string_topology__string_component_count`

Status: accepted active default Puzzle task.

## Identity
1. Domain: `puzzles`
2. Scene: `topology`
3. Scene id: `string_topology`
4. Public query id: `default`
5. Query id: `open_rope_count|closed_loop_count|knotted_component_count`

## Contract
1. Objective: count the requested kind of string component in one string-topology diagram.
2. Query branches:
   - `open_rope_count`: count open-ended rope components.
   - `closed_loop_count`: count closed loops, including knotted closed loops.
   - `knotted_component_count`: count components that contain at least one knot.
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `bbox_set`
5. Annotation contains one component bbox for each counted item.

## Notes
1. The renderer may use `string_strip`, `string_card`, or `string_outline` scene styling.
2. The scene contains separate ropes, rings, and knotted loops.
3. Internal trace metadata keeps the sampled branch in `query_id` and `internal_query_id`.
