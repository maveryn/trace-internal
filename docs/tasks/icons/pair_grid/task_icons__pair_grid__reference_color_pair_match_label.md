# `task_icons__pair_grid__reference_color_pair_match_label`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/reference_color_pair_match_label.py`
- prompt bundle: `icons_pair_grid_v1`

## Program Contract
`selection.reference_relation_match(scene=pair_grid, scope=labeled_scene_cells, reference_relation=left_right_color_pair, output=option_letter)`

scene=pair_grid
scope=labeled_scene_cells

## Contract
Renders a Reference before/after icon pair and a labeled Scene grid of six
before/after icon-pair cells, then asks which labeled Scene cell has the same
left and right colors as the Reference pair. Exactly one Scene cell is correct
by construction.

Supported query ids:
- `single`

Answer schema: `option_letter`.
Annotation schema: scalar `bbox` around the selected Scene cell.

## Notes
This task holds shape, size, and transform constant so the only answer-bearing
relation is the left/right color pair. Distractors include same-left/different-
right, different-left/same-right, reversed-color, and both-different color-pair
cases when the sampled palette permits them.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
