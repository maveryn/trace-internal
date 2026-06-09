# `task_misc__life_automaton__life_future_grid_label`

## Summary
1. Domain: `misc`
2. Task group: `automaton`
3. Task id: `task_misc__life_automaton__life_future_grid_label`
4. Scene id: `life_automaton`
5. Goal: apply a cellular-life neighbor rule and choose the option showing the future grid.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `one_step_future_grid|two_step_future_grid`
3. Answer type: `option_letter`
4. Annotation type: `keyed_bbox_map`
5. Annotation target: `source_grid` and `selected_option` bboxes
6. Scene variants: `clean_grid|lab_panel|notebook_grid`
7. Render metadata: records shared panel style, role-aware font family, unit-size jitter, and annotation-safe layout jitter before annotation projection.
8. Visual contract: source grid and option grids use the same rendered cell scale.
9. Scene-local variation: records `life_board.board_style`, `life_board.cell_palette_id`, resolved RGBs, and alive/dead/marker contrast checks.
