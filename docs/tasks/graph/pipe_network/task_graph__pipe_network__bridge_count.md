# `task_graph__pipe_network__bridge_count`

## 1) Identity
1. Domain: `graph`
2. Scene: `counting`
3. Scene id: `pipe_network`
4. Task id: `task_graph__pipe_network__bridge_count`
5. Objective: count open pipes whose removal disconnects part of the open-pipe network.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `pipe_bridge_count`
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `segment_set`
5. Only open pipes can be bridges; blocked pipes are ignored by the graph computation.
6. Annotation is an unordered `segment_set`; each segment is `[[x1, y1], [x2, y2]]` and connects the endpoint junction centers of one bridge pipe. Endpoint order inside each segment is semantically unordered.
7. Default bridge-pipe answer support is `0..5`.
8. Rendering uses compact letter/number junction labels and physical pipe-board styling with cylindrical tubes, flanged junction fittings, sampled board treatments, and clear blocked-pipe valve/X markers.

## 3) Prompt Contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `single_graph_counting`
3. `task_key`: `bridge_count_query`
4. Answer-only JSON: `{"answer":2}`
5. Answer+annotation JSON: `{"annotation":[[[180,220],[310,220]],[[310,220],[430,300]]],"answer":2}`

## 4) Verification
1. The verifier payload records open edge labels, blocked edge labels, and the bridge-edge witness set.
2. `answer_gt.value == len(annotation_gt.value)`.
3. Bridge status is recomputed from the finalized open-pipe graph.
