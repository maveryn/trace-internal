# `task_icons__named_grid__scoped_attribute_count`

- domain: `icons`
- scene_id: `named_grid`
- task: `scoped_attribute_count`
- module: `trace/tasks/icons/named_grid/scoped_attribute_count.py`

## Program Contract
`count.scoped_attribute(scene=named_grid, scope=numbered_row_or_column, attribute=shape, output=count)`

1. The image shows one visible grid with numbered rows and numbered columns.
2. Each grid cell contains one procedural named icon.
3. The prompt names one target icon shape in quotes and addresses one row or
   one column by number.
4. The answer is the number of target-shape icons in the addressed row or
   column.
5. `answer_gt.type = integer`.
6. `annotation_gt.type = point_set` over the center points of the counted
   target-shape icons only. `projected_annotation` mirrors this as typed
   point-set annotation with `point_set` and `pixel_point_set`.

## Query IDs
- `row_shape_count`
- `column_shape_count`

## Generation
Default answer support is `1..5`. Grid sizes are sampled from every
row/column combination in `4..6`:

- `4 x 4`
- `4 x 5`
- `4 x 6`
- `5 x 4`
- `5 x 5`
- `5 x 6`
- `6 x 4`
- `6 x 5`
- `6 x 6`

The selected grid size must have enough cells in the queried row or column to
support the sampled answer. The queried line contains exactly the sampled
answer count of the target shape. Additional target-shape icons are placed
outside the queried row/column as distractors so the task requires row/column
localization rather than whole-image counting.

Fill style and color are rendered as non-semantic visual variation.

## Trace
The trace records:
- every named icon with row/column indices, row/column numbers, cell bbox, and
  icon bbox,
- the target shape id/name,
- the queried axis and one-based row/column number,
- the counted cells and off-line target distractor cells,
- render-style metadata for the panel title and row/column number-label text
  legibility,
- query, answer, grid-size, line-index, shape, and fill-style probability
  metadata.
