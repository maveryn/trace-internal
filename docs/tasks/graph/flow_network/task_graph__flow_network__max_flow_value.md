# `task_graph__flow_network__max_flow_value`

## Summary
1. Domain: `graph`
2. Scene id: `flow_network`
3. Task id: `task_graph__flow_network__max_flow_value`
4. Objective: compute the maximum flow value from source `S` to sink `T`.
5. Implementation: `trace/tasks/graph/flow_network/max_flow_value.py`.

## Query IDs
1. Supported `query_id` values: `single`
2. Internal prompt key: `max_flow_value`.
3. Public sampling is at the task-id level.

## Taxonomy Contract
1. Program contract: read a directed capacity graph, find the unique minimum `S`-`T` cut, and return its capacity as the maximum-flow value.
2. Answer schema: `integer`.
3. Annotation schema: `segment_set`.
4. Node count, capacity values, cut-edge count, distractor-edge count, graph style, font, background, and layout transform are generation/render metadata, not public query branches.

## Program Contract
- `value(max_flow(source=S, sink=T, directed_capacity_graph)); output=integer; annotation=segment_set(unique_minimum_cut_edges); scene=flow_network; scope=max_flow_value`

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `segment_set`.
3. Annotation marks every directed edge in the unique minimum `S`-`T` cut as a pixel-space segment between endpoint node centers.
4. The answer equals the sum of capacities on the annotated cut edges.

## Rendering Contract
1. The scene shows one directed capacity network with highlighted `S` and `T` nodes.
2. Every visible directed edge has a readable integer capacity label.
3. Visual style, fonts, context text, background, layout transform, and post-render noise are non-semantic and recorded in trace metadata.
4. Annotation projection is computed after final graph layout and image-level variation.

## Prompt Contract
1. Prompt text comes from `prompts/graph/flow_network/graph_flow_network_v1.json`.
2. `scene_key`: `capacity_network`.
3. `task_key`: `flow_network_query`.
4. `query_key`: `max_flow_value`.
5. Answer-only mode emits `{"answer": ...}`.
6. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with `annotation` matching the `segment_set` schema.
