# `task_icons__pair_grid__attribute_delta_pair_count`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/attribute_delta_pair_count.py`
- prompt bundle: `icons_pair_grid_v1`

## Contract
Renders a Reference pair and a labeled Scene grid of icon pairs, then asks how
many Scene cells show the same color/size before-to-after attribute relation as
the Reference pair.
The Scene grid always contains 6 labeled option cells with fixed row-major
labels `A..F`; generation randomizes pair content, not label positions.

Query ids:
- `single`

Answer schema: integer.
Annotation schema: `bbox_set` around matching Scene cells.

## Program Contract
`count.reference_relation_match(scene=pair_grid, scope=labeled_scene_cells, reference_relation=color_size_delta, output=integer)`

The task counts labeled Scene cells whose before-to-after color/size attribute
delta matches the Reference pair. The sampled attribute-rule support is
`color_only_change|size_only_change|color_and_size_change` and is recorded as
trace metadata, not as public query ids, because the prompt operation is stable.

## Notes
Attribute-change branches compare color and size edits.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
