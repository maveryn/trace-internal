# `task_misc__life_automaton__life_population_count`

## Summary
1. Domain: `misc`
2. Task group: `automaton`
3. Task id: `task_misc__life_automaton__life_population_count`
4. Scene id: `life_automaton`
5. Goal: count dark cells in a marked row or column of the shown future grid.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `marked_line_live_count`
3. Answer type: `integer`
4. Annotation type: `bbox_set`
5. Annotation target: marked row or column bbox
6. Scene variants: `clean_grid|lab_panel|notebook_grid`
7. Render metadata: records shared panel style, role-aware font family, unit-size jitter, and annotation-safe layout jitter before annotation projection.
8. Scene-local variation: records `life_board.board_style`, `life_board.cell_palette_id`, resolved RGBs, and alive/dead/marker contrast checks.
