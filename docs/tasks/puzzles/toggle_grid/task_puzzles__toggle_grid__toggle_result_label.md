# `task_puzzles__toggle_grid__toggle_result_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `toggle_grid`
3. Source scene package: `toggle_grid`
4. Task id: `task_puzzles__toggle_grid__toggle_result_label`

## Query Contract
1. Supported `query_id`: `single`
2. Prompt asks for the labeled result grid produced by applying the numbered switch presses.
3. Internal variation: grid size, press sequence, option label, scene variant, and style are generation/render metadata.

## Program Contract
`select_label(result_grid_options, option_grid = simulate(start_grid, rule=orthogonal_toggle, actions=numbered_switch_sequence)); scene=toggle_grid; scope=toggle_result_label`

1. Program code: `simulation.discrete_state_update`
2. Scene: `toggle_grid`
3. Scope: `toggle_result_label`
4. Candidate set: visual result-grid option panels labeled `A`..`E`.
5. Transition rule: each press flips the chosen cell and any up/down/left/right neighbors present.
6. Answer binding: selected result option letter.
7. Annotation binding: one image-pixel `bbox` around the selected result option panel.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `annotation_gt.type = bbox`
3. Annotation schema: scalar `bbox`
4. Annotation target: the correct result option panel.
5. `scalar_annotation_checked = true`.

## Prompt Contract
1. Bundle: `puzzles_toggle_grid_v1`
2. Scene key: `toggle_grid`
3. Task key: `toggle_result_label_query`
4. Query key: `toggle_result_label`
