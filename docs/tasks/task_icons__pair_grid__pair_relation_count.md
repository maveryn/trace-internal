# `task_icons__pair_grid__pair_relation_count`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- task_group: `transformation`
- module: `trace/tasks/icons/transformation/pair_count.py`
- prompt bundle: `icons_transformation_v0`

## Contract
Renders a Reference pair and a labeled Scene grid of icon pairs, then asks how
many Scene cells show the same before-to-after relation as the Reference pair.
The Scene grid always contains 6 labeled option cells.

Query ids:
- `color_only_change`
- `size_only_change`
- `color_and_size_change`
- `same_pair_transform`

Answer schema: integer.
Evidence schema: `bbox_set` around matching Scene cells.

## Notes
Attribute-change branches compare color and size edits. The geometric branch
uses asymmetric icons and the transform vocabulary
`rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti`.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.

## Current Review Status
Current browser-review sidecars live under
`review/task-reviews/icons/pair_grid/task_icons__pair_grid__pair_relation_count/`.
Solve-rate status is tracked in `review/calibration_sweep_status.json`.
