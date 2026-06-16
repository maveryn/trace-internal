# `task_icons__pair_grid__reference_transform_match_count`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/reference_transform_match_count.py`
- prompt bundle: `icons_pair_grid_v1`

## Contract
Renders a Reference pair and a labeled Scene grid of icon pairs, then asks how
many Scene cells show the same before-to-after relation as the Reference pair.
The Scene grid always contains 6 labeled option cells with fixed row-major
labels `A..F`; generation randomizes pair content, not label positions.

Query ids:
- `single`

Answer schema: integer.
Annotation schema: `point_set` over the center points of matching Scene cells.

## Program Contract
`count.reference_relation_match(scene=pair_grid, scope=labeled_scene_cells, reference_relation=geometric_transform, output=integer)`

The task counts labeled Scene cells whose before-to-after geometric transform
matches the Reference pair. The sampled transform id is recorded as trace
metadata, not as a public query id, because the prompt operation is stable.

## Notes
The geometric branch uses asymmetric icons and the transform vocabulary
`rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti`.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
