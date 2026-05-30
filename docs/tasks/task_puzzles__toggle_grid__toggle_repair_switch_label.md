# `task_puzzles__toggle_grid__toggle_repair_switch_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Scene id: `toggle_grid`
4. Goal: choose the one lettered switch press that transforms the start grid into the target grid.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `toggle_repair_switch_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence target: start-grid panel bbox, target-grid panel bbox, and selected switch-cell bbox.
6. The verifier applies the recorded toggle rule to each recorded candidate switch, not pixels.
