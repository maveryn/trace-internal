# `task_puzzles__color_gradient__color_gradient_completion_label`

## Program Contract
`complete_linear_gradient(visible_swatch_sequence, missing_position, option_swatches); scene=color_gradient; scope=color_gradient_completion_label`

The scene shows a row of color swatches with one blank position and labeled
color-option swatches. Exactly one option fits the missing position in the
linear color gradient. The task returns that option's capital-letter label.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the selected option label.
3. `annotation_gt.type = bbox`
4. Annotation schema: `bbox`
5. Annotation is the image-pixel bounding box of the selected option swatch.
6. `scalar_annotation_checked = true`; this task always has one selected option
   witness. The blank swatch is context recorded in trace metadata.

## Query Contract
1. Public `query_id`: `single`
2. Internal trace metadata may vary sequence length, option count, color rule,
   missing position, scene variant, font, unit-size jitter, and answer label.
3. These generation axes do not change the answer schema, annotation schema, or
   reasoning program.

## Prompt Contract
1. Bundle: `puzzles_color_gradient_v1`
2. Scene key: `color_gradient`
3. Task key: `color_gradient_completion_query`
4. Prompt query key: `linear_gradient_completion_label`
