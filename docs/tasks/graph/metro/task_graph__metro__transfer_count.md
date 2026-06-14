# `task_graph__metro__transfer_count`

## 1) Identity
1. Domain: `graph`
2. Scene: `path`
3. Scene id: `metro`
4. Task id: `task_graph__metro__transfer_count`
5. Objective: count the minimum colored-route changes for a metro trip from a source station to a goal station through a required via station.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `metro_transfer_count`
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `point_sequence`
5. The sampled source, via, and goal stations have one selected minimum-transfer station path after shortest-path tie-breaking.
6. Annotation is the ordered station-center pixel sequence along the selected path in travel order: source first, via somewhere in the sequence, and goal last.

## 3) Prompt Contract
1. Bundle: `graph_path_v0`
2. `scene_key`: `metro_route_path`
3. `task_key`: `metro_transfer_count_query`
4. Answer-only JSON: `{"answer":2}`
5. Answer+annotation JSON: `{"annotation":[[180,220],[310,180],[430,260]],"answer":2}`

## 4) Verification
1. The verifier payload records source, via, goal, station adjacency, selected route sequence, route-change station labels, and the projected station path.
2. `answer_gt.value` equals the number of route-id changes in the selected route sequence.
3. Answers and annotation are computed from the same finalized metro route membership and adjacency metadata.
