# `task_puzzles__toggle_grid__toggle_repair_switch_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `toggle_grid`
3. Source scene package: `toggle_grid`
4. Task id: `task_puzzles__toggle_grid__toggle_repair_switch_label`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks for the one lettered start-grid switch that transforms the start grid into the target grid.
3. Internal variation: grid size, selected switch, option label, scene variant, and style are generation/render metadata.

## Program Contract
`select_label(candidate_switch_cells, cell = inverse_one_step_toggle(start_grid, target_grid, rule=orthogonal_toggle)); scene=toggle_grid; scope=toggle_repair_switch_label`

1. Program code: `simulation.discrete_state_update`
2. Scene: `toggle_grid`
3. Scope: `toggle_repair_switch_label`
4. Candidate set: lettered switch cells in the start grid.
5. Transition rule: each candidate press flips the chosen cell and any up/down/left/right neighbors present.
6. Answer binding: selected switch label.
7. Annotation binding: one image-pixel `bbox` around the selected switch cell.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `annotation_gt.type = bbox`
3. Annotation schema: scalar `bbox`
4. Annotation target: the start-grid cell containing the correct switch label.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_toggle_grid_v1`
2. Scene key: `toggle_grid`
3. Task key: `toggle_repair_switch_label_query`
4. Query key: `toggle_repair_switch_label`
