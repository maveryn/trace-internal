# `task_graph__metro__route_condition_station_count`

## Summary
1. Domain: `graph`
2. Scene id: `metro`
3. Task id: `task_graph__metro__route_condition_station_count`
4. Objective: count stations on a named colored route that satisfy a route-membership condition.
5. Implementation: `trace/tasks/graph/metro/route_condition_station_count.py`.

## Query IDs
1. Supported `query_id` values: `metro_route_transfer_station_count`, `metro_route_single_route_station_count`.
2. Internal prompt keys match the supported query ids.

## Taxonomy Notes
1. Program contract: count stations on one named route that satisfy the queried route-membership predicate.
2. Answer schema: `integer`.
3. Annotation schema: `point_set`.
4. Named route, route count, station labels, route colors, style, font, background, and layout jitter are generation/render metadata, not public query branches.

## Program Contract
- `count(station where station_on_route(named_route) and route_membership(station) satisfies queried_predicate); output=integer; annotation=point_set(matching_station_centers); scene=metro; scope=route_condition_station_count`

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_set`.
3. Annotation marks one `[x,y]` station-center point per station on the named route satisfying the queried condition.
4. The annotation is an empty array when no station on the named route satisfies the queried condition.
5. For `metro_route_transfer_station_count`, counted stations are on the named route and served by at least two colored routes.
6. For `metro_route_single_route_station_count`, counted stations are on the named route and served only by that route.

## Rendering Contract
1. The scene shows a labeled metro route map with colored routes and station nodes.
2. Route names are visible in the route legend.
3. Transfer stations are visually indicated by multi-route overlap and larger station styling.

## Prompt Contract
1. Prompt text comes from `prompts/graph/metro/graph_metro_v1.json`.
2. `scene_key`: `metro_route_map`.
3. `task_key`: `metro_route_query`.
4. `query_key`: selected supported `query_id`.
