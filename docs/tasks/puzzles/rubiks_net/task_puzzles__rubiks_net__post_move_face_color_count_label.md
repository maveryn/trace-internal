# `task_puzzles__rubiks_net__post_move_face_color_count_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `rubiks_net`
3. Source scene package: `rubiks_net`
4. Task id: `task_puzzles__rubiks_net__post_move_face_color_count_label`

## Query Contract
1. Supported `query_id`: `single`
2. Internal question format: `post_move_face_color_count_label`
3. Prompt asks for the number-option label matching a target-color face count after applying a visible move sequence.
4. Internal variation: move count, move tokens, target face, target swatch, option order, scene treatment, and style are generation/render metadata.

## Program Contract
`select_label(number_option, rule=apply_move_sequence_then_count_target_color_on_face); scene=rubiks_net; scope=post_move_face_color_count_label`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct number option panel.
3. `annotation_gt.type = bbox`
4. Annotation schema: scalar `bbox`
5. Annotation target: one bbox around the selected option panel.
6. `scalar_annotation_checked = true`.

## Trace Contract
1. `execution_trace.rubiks_rule_code = post_move_face_color_count`.
2. `execution_trace.query_sequence` and `execution_trace.counted_sticker_ids` record the solved state and count.
3. `render_map.option_panel_bboxes_px` contains the selected option panel bbox projected into `annotation_gt`.

## Prompt Contract
1. Bundle: `puzzles_rubiks_net_v1`
2. Scene key: `rubiks_net`
3. Task key: `post_move_face_color_count_label_query`
4. Query key: `post_move_face_color_count_label`
