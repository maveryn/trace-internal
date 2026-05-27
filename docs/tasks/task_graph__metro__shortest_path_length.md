# `task_graph__metro__shortest_path_length`

## 1) Identity
1. Domain: `graph`
2. Task group: `path`
3. Scene id: `metro`
4. Task id: `task_graph__metro__shortest_path_length`
5. Objective: count route segments in the unique shortest station path between two labeled stations.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `metro_shortest_path_length`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_sequence`
5. The sampled source and goal have exactly one shortest path in the metro adjacency graph.
6. Evidence is the ordered station-center pixel sequence along that unique shortest path, including both endpoints.

## 3) Prompt Contract
1. Bundle: `graph_path_v0`
2. `scene_key`: `metro_route_path`
3. `task_key`: `shortest_path_length_query`
4. Answer-only JSON: `{"answer":2}`
5. Answer+evidence JSON: `{"evidence":[[180,220],[310,180],[430,260]],"answer":2}`

## 4) Verification
1. The verifier payload records the source, goal, metro adjacency map, and ordered witness path.
2. `answer_gt.value == len(evidence_gt.value) - 1`.
3. Answers and evidence are computed from the same finalized metro adjacency map.
