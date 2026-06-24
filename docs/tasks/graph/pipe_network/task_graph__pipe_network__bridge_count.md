# `task_graph__pipe_network__bridge_count`

## Summary
1. Domain: `graph`
2. Scene id: `pipe_network`
3. Task id: `task_graph__pipe_network__bridge_count`
4. Objective: count open pipe segments whose removal disconnects part of the open-pipe network.
5. Implementation: `trace/tasks/graph/pipe_network/bridge_count.py`.

## Query IDs
1. Supported `query_id` values: `single`.
2. Internal prompt key: `pipe_bridge_count`.
3. Public sampling is at the task-id level.

## Taxonomy Contract
1. Program contract: compute all bridge edges in the open-pipe graph while ignoring blocked pipes.
2. Answer schema: `integer`.
3. Annotation schema: `segment_set`.
4. Target bridge count, node count, grid shape, label style, color, font, background, context text, and noise are generation/render metadata, not public query branches.

## Program Contract
- `count(open_pipe edge where removing edge disconnects open_pipe_graph); output=integer; annotation=segment_set(bridge_pipe_endpoint_center_segments); scene=pipe_network; scope=bridge_count`

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `segment_set`.
3. Annotation marks one `[[x0,y0],[x1,y1]]` node-center segment per bridge pipe.
4. Segment endpoint order is not semantic.
5. The answer equals the number of annotation segments, and both come from the same finalized open-pipe graph.

## Rendering Contract
1. The scene shows labeled junction fittings connected by open pipes and visible blocked pipes.
2. Blocked pipes are visible distractors and are ignored by the bridge computation.
3. Visual style, fonts, panel treatment, layout jitter, context text, and post-render noise are non-semantic and recorded in trace metadata.
4. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/pipe_network/graph_pipe_network_v1.json`.
2. `scene_key`: `pipe_network`.
3. `task_key`: `pipe_network_query`.
4. `query_key`: `pipe_bridge_count`.
5. Answer-only mode emits `{"answer": ...}`.
6. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with `annotation` matching the `segment_set` schema.
