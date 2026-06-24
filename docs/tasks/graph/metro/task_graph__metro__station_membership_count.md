# `task_graph__metro__station_membership_count`

## Summary
1. Domain: `graph`
2. Scene id: `metro`
3. Task id: `task_graph__metro__station_membership_count`
4. Objective: count stations satisfying a route-membership predicate.
5. Implementation: `trace/tasks/graph/metro/station_membership_count.py`.

## Query IDs
1. Supported `query_id` values: `metro_transfer_station_count`, `metro_single_route_station_count`.
2. Internal prompt keys match the supported query ids.
3. Public sampling is at the task-id level; the two branches are semantic route-membership predicates under the same count contract.

## Taxonomy Contract
1. Program contract: count all station nodes whose route-membership cardinality satisfies the queried predicate.
2. Answer schema: `integer`.
3. Annotation schema: `point_set`.
4. Route count, station labels, route colors, style, font, background, and layout jitter are generation/render metadata, not public query branches.

## Program Contract
- `count(station where route_membership(station) satisfies queried_predicate); output=integer; annotation=point_set(matching_station_centers); scene=metro; scope=station_membership_count`

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_set`.
3. Annotation marks one `[x,y]` station-center point per matching station.
4. The answer equals the number of annotation points, and both come from the same finalized metro-route graph.

## Rendering Contract
1. The scene shows a labeled metro route map with colored routes and station nodes.
2. Transfer stations are visually indicated by multi-route overlap and larger station styling.
3. Visual style, fonts, panel treatment, layout jitter, context text, and post-render noise are non-semantic and recorded in trace metadata.
4. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/metro/graph_metro_v1.json`.
2. `scene_key`: `metro_route_map`.
3. `task_key`: `metro_route_query`.
4. `query_key`: selected supported `query_id`.
5. Answer-only mode emits `{"answer": ...}`.
6. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with `annotation` matching the `point_set` schema.
