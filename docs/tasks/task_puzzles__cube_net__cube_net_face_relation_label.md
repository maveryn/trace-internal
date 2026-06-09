# `task_puzzles__cube_net__cube_net_face_relation_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Scene id: `cube_net`
4. Goal: use a labeled cube net to identify a face by folded-cube relation.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `opposite_face_label|marked_edge_neighbor_face_label`
3. Answer type: `option_letter`
4. Annotation type: `keyed_bbox_map`
5. Annotation keys: `marked_face` and `selected_option`.
6. The verifier uses finalized face labels, net geometry, and cube-face adjacency metadata, not pixels.
7. Render metadata records the sampled shared panel style, visible cube-net scene variant, role-aware font family, and post-image noise policy.
