# `task_icons__paired_canvas__panel_set_relation_count`

## Identity
- domain: `icons`
- scene_id: `paired_canvas`
- task_group: `counting`
- module: `trace/tasks/icons/counting/panel_set_relation_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders two icon panels labeled `Left` and `Right`, then asks for a set relation
between the panels.

Query ids:
- `right_exact_match_count`
- `added_in_right_count`
- `missing_from_right_count`

Answer schema: integer.
Annotation schema: `bbox_set`; exact-match and added-icon queries box counted
Right-panel icons, while missing-icon queries box counted Left-panel icons.
`projected_annotation` mirrors this as typed bbox-set annotation with `bbox_set`,
`pixel_bbox_set`, and bbox-center `pixel_point_set`.

## Notes
Exact matches are defined over icon type, color, size, and rotation. Added and
missing identities are sampled distinctly so panel membership is unambiguous.
Render metadata records panel-title text legibility.
