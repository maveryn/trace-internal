# `task_icons__pair_grid__reference_transform_match_label`

## Identity
- domain: `icons`
- scene_id: `pair_grid`
- module: `trace/tasks/icons/pair_grid/reference_transform_match_label.py`
- prompt bundle: `icons_pair_grid_v1`

## Program Contract
`selection.reference_relation_match(scene=pair_grid, scope=labeled_scene_cells, reference_relation=geometric_transform, output=option_letter)`

scene=pair_grid
scope=labeled_scene_cells

## Contract
Renders a Reference before/after icon pair and a labeled Scene grid of six
before/after icon-pair cells, then asks which labeled Scene cell shows the same
geometric transformation as the Reference pair. Exactly one Scene cell is
correct by construction.

Supported query ids:
- `single`

Answer schema: `option_letter`.
Annotation schema: scalar `bbox` around the selected Scene cell.

## Notes
The geometric transform id is sampled from
`rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti` and recorded
as trace metadata, not as a public query id. The task uses asymmetric icons so
distractor transforms remain visually distinct from the Reference transform.

Renderer metadata records sampled palette/style, panel-header and cell-label
text-legibility metadata, and per-icon noise edits.
