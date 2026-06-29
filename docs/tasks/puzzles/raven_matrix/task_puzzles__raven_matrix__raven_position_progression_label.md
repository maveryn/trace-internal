# `task_puzzles__raven_matrix__raven_position_progression_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `raven_matrix`
3. Source scene package: `raven_matrix`
4. Task id: `task_puzzles__raven_matrix__raven_position_progression_label`

## Query Contract
1. Supported `query_id`: `single`
2. Internal question format: `raven_position_progression_label`
3. Prompt asks for the option that completes the missing lower-right Raven matrix cell under a marker-position progression rule.
4. Internal variation: marker path, option order, option label, scene treatment, and style are generation/render metadata.

## Program Contract
`select_label(raven_option, rule=position_progression_matrix_completion); scene=raven_matrix; scope=raven_position_progression_label`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct option panel.
3. `annotation_gt.type = bbox`
4. Annotation schema: scalar `bbox`
5. Annotation target: one bbox around the correct option panel.
6. `scalar_annotation_checked = true`.

## Trace Contract
1. `execution_trace.raven_rule_code = position_progression_matrix`.
2. `execution_trace.option_specs` records all option panels, labels, and the unique correct option.
3. `render_map.option_panel_bboxes_px` contains the selected option panel bbox projected into `annotation_gt`.

## Prompt Contract
1. Bundle: `puzzles_raven_matrix_v1`
2. Scene key: `raven_matrix`
3. Task key: `raven_position_progression_label_query`
4. Query key: `raven_position_progression_label`
