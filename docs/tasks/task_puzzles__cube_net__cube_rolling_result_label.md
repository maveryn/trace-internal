# `task_puzzles__cube_net__cube_rolling_result_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Scene id: `cube_net`
4. Goal: roll a labeled cube along a visible arrow path and choose the requested final face label.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `final_top_face_label|final_front_face_label|final_right_face_label`
3. Answer type: `option_letter`
4. Evidence type: `keyed_bbox_map`
5. Evidence keys: `start_cube`, `roll_path`, and `selected_option`.
6. The verifier simulates the recorded cube orientation and path directions, not pixels.
7. Render metadata records the sampled shared panel style, visible cube-net scene variant, role-aware font family, and post-image noise policy.
