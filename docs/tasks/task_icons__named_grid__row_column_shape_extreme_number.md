# `task_icons__named_grid__row_column_shape_extreme_number`

- domain: `icons`
- scene_id: `named_grid`
- task_group: `counting`
- task: `row_column_shape_extreme_number`
- module: `trace/tasks/icons/counting/named_grid_row_column_shape_extreme_number.py`

## Contract
1. The image shows one visible grid with numbered rows and numbered columns.
2. Each grid cell contains one procedural named icon.
3. The prompt names one target icon shape in quotes and asks which row or
   column has the most or fewest target-shape icons.
4. The answer is the one-based row or column number with the unique extreme.
5. `answer_gt.type = integer`.
6. `annotation_gt.type = bbox_set` over the target-shape icons in the selected
   row or column. `projected_annotation` mirrors this as typed bbox-set annotation
   with `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.

## Query IDs
- `row_most_shape_number`
- `row_fewest_shape_number`
- `column_most_shape_number`
- `column_fewest_shape_number`

## Generation
Default answer-line support is `1..6`. Grid sizes are sampled from every
row/column combination in `4..6`.

The selected row or column has a unique target-shape count extreme by
construction. For most-count queries, every other row or column has fewer
target-shape icons. For fewest-count queries, every other row or column has
more target-shape icons. The winning line contains at least one target icon so
prompt-facing annotation is non-empty.

Fill style and color are rendered as non-semantic visual variation.

## Trace
The trace records:
- every named icon with row/column indices, row/column numbers, cell bbox, and
  icon bbox,
- the target shape id/name,
- the queried axis, extremum, selected row/column number, and winning count,
- row and column target-shape counts,
- selected-line target cells and off-line target distractor cells,
- render-style metadata for the panel title and row/column number-label text
  legibility,
- query, answer-line, grid-size, winning-count, shape, and fill-style
  probability metadata.
