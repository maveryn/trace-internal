# `task_graph__metro__exact_distance_station_count`

## 1) Identity
1. Domain: `graph`
2. Scene: `relation`
3. Scene id: `metro`
4. Task id: `task_graph__metro__exact_distance_station_count`
5. Objective: count stations at shortest metro-route distance exactly `k` route segments from a queried station.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `metro_exact_distance_count`
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `point_set`
5. Distances are computed over adjacent station-to-station route segments.
6. Annotation is an unordered set of station-center pixel points for all stations at the queried distance.
7. Current calibrated support uses `route_count=2..3`, letter/number/named station labels, `k=2`, and answer values `1..5`.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `metro_route_relation`
3. `task_key`: `exact_distance_count_query`
4. Answer-only JSON: `{"answer":3}`
5. Answer+annotation JSON: `{"annotation":[[180,220],[310,180],[430,260]],"answer":3}`

## 4) Verification
1. The verifier payload records the queried station, queried distance, adjacency map, and exact-distance witness set.
2. `answer_gt.value == len(annotation_gt.value)`.
3. Answers and annotation are computed from the same finalized metro adjacency map.
