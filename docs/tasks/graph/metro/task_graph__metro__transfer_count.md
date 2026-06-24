# `task_graph__metro__transfer_count`

## Summary
1. Domain: `graph`
2. Scene id: `metro`
3. Task id: `task_graph__metro__transfer_count`
4. Objective: count the minimum colored-route changes for a metro trip from a source station to a goal station through a required via station.
5. Implementation: `trace/tasks/graph/metro/transfer_count.py`.

## Query IDs
1. Supported `query_id` values: `single`.
2. Internal prompt key: `metro_transfer_count`.
3. Public sampling is at the task-id level.

## Taxonomy Contract
1. Program contract: find the selected minimum-transfer station path from source to goal through the via station and output the number of route changes.
2. Answer schema: `integer`.
3. Annotation schema: `point_sequence`.
4. Transfer-count target, route count, station labels, route colors, style, font, background, and layout jitter are generation/render metadata, not public query branches.

## Program Contract
- `min_route_changes(path from source through via to goal); output=integer; annotation=point_sequence(selected_path_station_centers_in_order); scene=metro; scope=transfer_count`

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_sequence`.
3. Annotation marks ordered station-center points along the selected source-via-goal route, including endpoints and the via station.
4. The answer equals the number of route-id changes along the annotated route sequence, and both come from the same finalized metro-route graph.

## Rendering Contract
1. The scene shows a labeled metro route map with colored routes and station nodes.
2. The via station is visually highlighted.
3. Visual style, fonts, panel treatment, layout jitter, context text, and post-render noise are non-semantic and recorded in trace metadata.
4. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/metro/graph_metro_v1.json`.
2. `scene_key`: `metro_route_map`.
3. `task_key`: `metro_route_query`.
4. `query_key`: `metro_transfer_count`.
5. Answer-only mode emits `{"answer": ...}`.
6. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with `annotation` matching the `point_sequence` schema.
