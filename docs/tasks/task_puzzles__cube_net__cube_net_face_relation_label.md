# `task_puzzles__cube_net__cube_net_face_relation_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Scene id: `cube_net`
4. Goal: use a labeled cube net to identify a face by folded-cube relation.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `opposite_face_label|marked_edge_neighbor_face_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence target: marked reference face bbox followed by the selected option-panel bbox.
6. The verifier uses finalized face labels, net geometry, and cube-face adjacency metadata, not pixels.
