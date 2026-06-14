# `task_icons__pair_grid__attribute_delta_pair_count`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/attribute_delta_pair_count.py`
- prompt bundle: `icons_pair_grid_v0`

## Contract
Renders a Reference pair and a labeled Scene grid of icon pairs, then asks how
many Scene cells show the same color/size before-to-after attribute relation as
the Reference pair.
The Scene grid always contains 6 labeled option cells with fixed row-major
labels `A..F`; generation randomizes pair content, not label positions.

Query ids:
- `color_only_change`
- `size_only_change`
- `color_and_size_change`

Answer schema: integer.
Annotation schema: `bbox_set` around matching Scene cells.

## Notes
Attribute-change branches compare color and size edits.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
