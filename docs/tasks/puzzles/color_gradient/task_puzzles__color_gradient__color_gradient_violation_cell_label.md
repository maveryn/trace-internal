# `task_puzzles__color_gradient__color_gradient_violation_cell_label`

## Program Contract
`find_gradient_violation(swatch_grid, row_column_progression_rule); scene=color_gradient; scope=color_gradient_violation_cell_label`

The scene shows a labeled grid of color swatches. Exactly one visible swatch
breaks the smooth row/column color progression. The task returns the capital
letter printed on that swatch.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the violating swatch label.
3. `annotation_gt.type = bbox`
4. Annotation schema: `bbox`
5. Annotation is the image-pixel bounding box of the violating swatch cell.
6. `scalar_annotation_checked = true`; this task always has one visual witness.

## Query Contract
1. Public `query_id`: `single`
2. Internal trace metadata may vary grid size, progression rule, scene variant,
   font, unit-size jitter, and answer label.
3. These generation axes do not change the answer schema, annotation schema, or
   reasoning program.

## Prompt Contract
1. Bundle: `puzzles_color_gradient_v1`
2. Scene key: `color_gradient`
3. Task key: `color_gradient_violation_query`
4. Prompt query key: `color_gradient_violation_cell_label`
