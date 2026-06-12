# `task_puzzles__toggle_grid__toggle_result_label`

## Summary
1. Domain: `puzzles`
2. Scene: `logic`
3. Scene id: `toggle_grid`
4. Goal: apply numbered Lights-Out-style switch presses and choose the resulting grid.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `toggle_result_label`
3. Answer type: `option_letter`
4. Annotation type: `keyed_bbox_map`
5. Annotation target: keys `start_grid` and `selected_option`.
6. The verifier applies the recorded toggle rule to the recorded start state and pressed cells, not pixels.
