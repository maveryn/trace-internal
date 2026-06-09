# `task_graph__pipe_network__shortest_path_length`

## 1) Identity
1. Domain: `graph`
2. Task group: `path`
3. Scene id: `pipe_network`
4. Task id: `task_graph__pipe_network__shortest_path_length`
5. Objective: count open pipe segments in the unique shortest open route between two labeled junctions.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `pipe_shortest_path_length`
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `point_sequence`
5. The image shows labeled junctions connected by open pipes and blocked pipes.
6. Only open pipes are traversable; blocked pipes are visible distractors.
7. Annotation is the ordered pixel-point sequence of junction centers along the unique shortest open route, including both endpoints.
8. Rendering uses compact letter/number junction labels and physical pipe-board styling with cylindrical tubes, flanged junction fittings, sampled board treatments, and clear blocked-pipe valve/X markers.

## 3) Prompt Contract
1. Bundle: `graph_path_v0`
2. `scene_key`: `single_graph_path`
3. `task_key`: `shortest_path_length_query`
4. Answer-only JSON: `{"answer":2}`
5. Answer+annotation JSON: `{"annotation":[[180,220],[310,220],[430,300]],"answer":2}`

## 4) Verification
1. The verifier payload records the open adjacency, blocked pipe labels, source/goal labels, and witness path.
2. `answer_gt.value == len(annotation_gt.value) - 1`.
3. Answers and annotation are computed from the same open-pipe graph.
