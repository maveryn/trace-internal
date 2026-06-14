# `task_icons__named_grid__group_predicate_count`

- domain: `icons`
- scene_id: `named_grid`
- task: `group_predicate_count`
- module: `trace/tasks/icons/named_grid/group_predicate_count.py`

## Program Contract
1. The image shows one visible grid with numbered rows and numbered columns.
2. Each grid cell contains one procedural named icon.
3. The prompt names one target icon shape in quotes and asks how many rows or
   columns satisfy a count condition for that shape.
4. Supported conditions are at least `N`, exactly `N`, and no target-shape
   icons.
5. The answer is the number of qualifying rows or columns.
6. `answer_gt.type = integer`.
7. `annotation_gt.type = bbox_set` with one box around each qualifying row or
   column region. `projected_annotation` mirrors this as typed bbox-set annotation
   with `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.

## Query IDs
- `row_at_least_shape_count`
- `column_at_least_shape_count`
- `row_exactly_shape_count`
- `column_exactly_shape_count`
- `row_no_shape_count`
- `column_no_shape_count`

## Generation
Default answer support is `0..5`. Grid sizes are sampled from every row/column
combination in `4..6`.

For at-least queries, thresholds are sampled from `2..3`. For exactly queries,
thresholds are sampled from `1..3`. No-shape queries use threshold `0`.

The generator first samples the number of qualifying rows or columns, then
constructs target-shape counts so exactly that many lines satisfy the selected
condition. Fill style and color are rendered as non-semantic visual variation.

## Trace
The trace records:
- every named icon with row/column indices, row/column numbers, cell bbox, and
  icon bbox,
- the target shape id/name,
- the queried axis, condition, threshold, and answer count,
- row and column target-shape counts,
- qualifying row/column indices, numbers, and region bboxes,
- render-style metadata for the panel title and row/column number-label text
  legibility,
- query, answer, grid-size, threshold, shape, and fill-style probability
  metadata.
