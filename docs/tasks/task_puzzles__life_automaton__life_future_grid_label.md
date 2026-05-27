# `task_puzzles__life_automaton__life_future_grid_label`

## Summary
1. Domain: `puzzles`
2. Task group: `automaton`
3. Task id: `task_puzzles__life_automaton__life_future_grid_label`
4. Scene id: `life_automaton`
5. Goal: apply a cellular-life neighbor rule and choose the option showing the future grid.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `one_step_future_grid|two_step_future_grid`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence target: source-grid bbox followed by selected option bbox
6. Scene variants: `clean_grid|lab_panel|notebook_grid`
