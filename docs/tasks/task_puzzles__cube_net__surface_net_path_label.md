# `task_puzzles__cube_net__surface_net_path_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Scene id: `cube_net`
4. Goal: follow a path across folded cube-net edges and choose either the endpoint face or the visited-face sequence.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `folded_path_endpoint_label|folded_path_face_sequence_label`
3. Answer type: `option_letter`
4. Evidence type: `keyed_bbox_map`
5. Evidence keys: `start_face`, `move_instructions`, and `selected_option`.
6. The verifier uses the recorded cube-net face labels, folded-edge moves, and folded adjacency trace, not pixels.
7. Render metadata records the sampled shared panel style, visible cube-net scene variant, role-aware font family, and post-image noise policy.
