# `task_icons__named_grid__row_column_shape_count`

- domain: `icons`
- scene_id: `named_grid`
- task_group: `counting`
- task: `row_column_shape_count`
- module: `trace/tasks/icons/counting/named_grid_row_column_shape_count.py`

## Contract
1. The image shows one visible grid with numbered rows and numbered columns.
2. Each grid cell contains one procedural named icon.
3. The prompt names one target icon shape in quotes and addresses one row or
   one column by number.
4. The answer is the number of target-shape icons in the addressed row or
   column.
5. `answer_gt.type = integer`.
6. `evidence_gt.type = bbox_set` over the counted target-shape icons only.
   `projected_evidence` mirrors this as typed bbox-set evidence with
   `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.

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
