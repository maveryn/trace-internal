# `task_puzzles__color_gradient__color_gradient_completion_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `color_gradient`
3. Task group: `visual`
4. Task id: `task_puzzles__color_gradient__color_gradient_completion_label`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `linear_gradient_completion_label`
3. Prompt asks for the labeled option that completes a one-dimensional color gradient with one blank swatch.
4. Internal variation:
   - `sequence_length_variant`: `5_cell|6_cell|7_cell`
   - `option_count_variant`: supported `4_options|5_options|6_options`; current config samples `6_options`
   - `rule_variant`: `hue_gradient|lightness_gradient|hue_lightness_gradient`
   - `scene_variant`: `swatch_clean|swatch_card|swatch_notebook`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label of the correct option swatch.
3. `annotation_gt.type = keyed_bbox_map`
4. Annotation contains role-bound boxes:
   - `blank_swatch`: the blank sequence swatch.
   - `selected_option`: the answer option swatch.

## Trace Contract
1. `scene_ir.entities` includes one `linear_color_gradient_panel`, one `linear_gradient_sequence_cell` per row swatch, and one `linear_gradient_option_swatch` per answer option.
2. `render_map.item_bboxes_px` contains the blank cell id and all option ids.
3. `execution_trace.supporting_item_ids` records `[missing_cell_id, correct_option_id]`.
4. `execution_trace.rule_params` records the sampled color progression parameters.
5. `projected_annotation.keyed_bbox_map` and `pixel_keyed_bbox_map` store the public role-bound annotation boxes.

## Prompt Contract
1. Bundle: `puzzles_visual_v0`
2. Scene key: `color_gradient`
3. Task key: `color_gradient_completion_query`
4. Query key: `linear_gradient_completion_label`
5. Prompt text should describe the blank swatch and answer options, but should not expose the hidden HSL parameters.
6. Answer+annotation JSON shape: `{"annotation":{"blank_swatch":[268,188,372,292],"selected_option":[524,420,628,524]},"answer":"C"}`

## Visual Policy
1. All swatch and option labels use one deterministic font family sampled from the readout font pool and recorded in `render_spec.label_style.font`.
2. Post-image noise is intentionally disabled for this color-semantic task and recorded in `render_spec.post_image_noise_policy`.
