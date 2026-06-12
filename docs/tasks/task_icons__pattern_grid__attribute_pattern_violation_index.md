# `task_icons__pattern_grid__attribute_pattern_violation_index`

## Identity
- domain: `icons`
- scene_id: `pattern_grid`
- scene_id: `pattern`
- module: `trace/tasks/icons/pattern/grid_color_violation.py`
- prompt bundle: `icons_pattern_v0`

## Contract
Renders a numbered `3 x 3` icon grid where one numbered box violates a visible
attribute pattern.

Query ids:
- `grid_color_violation`
- `grid_size_violation`

Answer schema: integer numbered-box index.
Annotation schema: one-box `bbox_set` around the violating numbered box.
Projected annotation uses the shared icon bbox annotation shape with `type`,
`bbox_set`, `pixel_bbox_set`, and `pixel_point_set`.

## Notes
Color and size use separate internal generation/rendering branches, but share
the same public objective: identify the single attribute-pattern violation.
Renderer metadata records panel-header and numbered-cell text legibility.

## Current Review Status
Current browser-review sidecars live under
`review/task-reviews/icons/pattern_grid/task_icons__pattern_grid__attribute_pattern_violation_index/`.
Solve-rate status is tracked in `review/calibration_sweep_status.json`.
