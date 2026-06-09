# `task_puzzles__color_gradient__color_gradient_violation_cell_label`

## Summary
1. Domain: `puzzles`
2. Task group: `visual`
3. Scene id: `color_gradient`
4. Task id: `task_puzzles__color_gradient__color_gradient_violation_cell_label`
5. Goal: identify the labeled swatch cell whose color breaks a smooth grid progression.
6. Default dataset status: registered and default-enabled.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `color_gradient_violation_cell_label`
3. Answer type: `option_letter`
4. Annotation type: `bbox_set`
5. Annotation target: exactly one bbox for the violating swatch cell.
6. Supported grid sizes: `3x3|4x4`
7. Supported `scene_variant` values: `swatch_clean|swatch_card|swatch_notebook`
8. Supported internal `rule_variant` values:
   - `column_hue_row_lightness`
   - `row_hue_column_lightness`
   - `column_hue_row_saturation`

## Trace
1. `scene_ir.entities` includes one `color_gradient_panel` plus one `color_gradient_swatch_cell` per labeled swatch.
2. `render_map.cell_bboxes_px` and `render_map.item_bboxes_px` map each `cell_<LABEL>` id to its pixel bbox.
3. `execution_trace.cells` records each cell label, row/column index, expected HSL/RGB, observed HSL/RGB, and `is_violation`.
4. `execution_trace.violation_cell_id` and `execution_trace.answer_label` identify the answer cell.
5. Prompt-facing annotation is projected from the violating cell bbox, not inferred from pixels.
6. `render_spec.label_style.font` records the sampled readout font family used for all swatch labels.
7. `render_spec.post_image_noise_policy` records the intentional no-noise override for color-semantic separability.

## Prompt
1. Bundle: `puzzles_visual_v0`
2. Scene key: `color_gradient`
3. Task key: `color_gradient_violation_query`
4. Query key: `color_gradient_violation_cell_label`
5. Answer+annotation JSON shape: `{"annotation":[[324,188,432,296]],"answer":"F"}`
6. Answer-only JSON shape: `{"answer":"F"}`
