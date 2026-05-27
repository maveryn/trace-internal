# `task_puzzles__cube_net__cube_rolling_result_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Scene id: `cube_net`
4. Goal: roll a labeled cube along a visible arrow path and choose the requested final face label.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `final_top_face_label|final_front_face_label|final_right_face_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence target: start-cube panel bbox, roll-path panel bbox, and selected option-panel bbox.
6. The verifier simulates the recorded cube orientation and path directions, not pixels.
