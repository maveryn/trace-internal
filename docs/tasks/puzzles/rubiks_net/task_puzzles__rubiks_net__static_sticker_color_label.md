# `task_puzzles__rubiks_net__static_sticker_color_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `rubiks_net`
3. Source scene package: `rubiks_net`
4. Task id: `task_puzzles__rubiks_net__static_sticker_color_label`

## Query Contract
1. Supported `query_id`: `single`
2. Internal question format: `static_sticker_color_label`
3. Prompt asks for the color-swatch option matching one visible sticker at a named face coordinate.
4. Internal variation: target face/coordinate, scramble, palette, option order, scene treatment, and style are generation/render metadata.

## Program Contract
`select_label(color_swatch_option, rule=read_visible_cube_net_sticker_color); scene=rubiks_net; scope=static_sticker_color_label`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct swatch option panel.
3. `annotation_gt.type = bbox`
4. Annotation schema: scalar `bbox`
5. Annotation target: one bbox around the selected option panel.
6. `scalar_annotation_checked = true`.

## Trace Contract
1. `execution_trace.rubiks_rule_code = static_sticker_color_readout`.
2. `execution_trace.target_sticker_id` records the sticker read from the cube net.
3. `render_map.option_panel_bboxes_px` contains the selected option panel bbox projected into `annotation_gt`.

## Prompt Contract
1. Bundle: `puzzles_rubiks_net_v1`
2. Scene key: `rubiks_net`
3. Task key: `static_sticker_color_label_query`
4. Query key: `static_sticker_color_label`
