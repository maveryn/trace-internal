# `task_puzzles__rubiks_net__static_face_color_count_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `rubiks_net`
3. Source scene package: `rubiks_net`
4. Task id: `task_puzzles__rubiks_net__static_face_color_count_label`

## Query Contract
1. Supported `query_id`: `single`
2. Internal question format: `static_face_color_count_label`
3. Prompt asks for the number-option label matching the count of target-color stickers on one face.
4. Internal variation: target face, target swatch, scramble, option order, scene treatment, and style are generation/render metadata.

## Program Contract
`select_label(number_option, rule=count_target_color_on_visible_face); scene=rubiks_net; scope=static_face_color_count_label`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct number option panel.
3. `annotation_gt.type = bbox`
4. Annotation schema: scalar `bbox`
5. Annotation target: one bbox around the selected option panel.
6. `scalar_annotation_checked = true`.

## Trace Contract
1. `execution_trace.rubiks_rule_code = static_face_color_count`.
2. `execution_trace.counted_sticker_ids` records the counted stickers.
3. `render_map.option_panel_bboxes_px` contains the selected option panel bbox projected into `annotation_gt`.

## Prompt Contract
1. Bundle: `puzzles_rubiks_net_v1`
2. Scene key: `rubiks_net`
3. Task key: `static_face_color_count_label_query`
4. Query key: `static_face_color_count_label`
