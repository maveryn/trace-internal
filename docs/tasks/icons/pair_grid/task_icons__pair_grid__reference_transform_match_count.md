# `task_icons__pair_grid__reference_transform_match_count`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/reference_transform_match_count.py`
- prompt bundle: `icons_pair_grid_v0`

## Contract
Renders a Reference pair and a labeled Scene grid of icon pairs, then asks how
many Scene cells show the same before-to-after relation as the Reference pair.
The Scene grid always contains 6 labeled option cells with fixed row-major
labels `A..F`; generation randomizes pair content, not label positions.

Query ids:
- `same_pair_transform`

Answer schema: integer.
Annotation schema: `bbox_set` around matching Scene cells.

## Notes
The geometric branch uses asymmetric icons and the transform vocabulary
`rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti`.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
