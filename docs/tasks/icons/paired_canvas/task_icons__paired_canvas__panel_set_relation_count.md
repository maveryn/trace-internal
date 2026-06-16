# `task_icons__paired_canvas__panel_set_relation_count`

## Identity
- domain: `icons`
- scene_id: `paired_canvas`
- scene package: `paired_canvas`
- module: `trace/tasks/icons/paired_canvas/panel_set_relation_count.py`
- prompt bundle: `icons_paired_canvas_v0`

## Program Contract
`count.set_relation(scene=paired_canvas, scope=left_right_icon_panels, relation=right_exact_match|added_in_right|missing_from_right, output=count)`

The program compares the two rendered icon panels and counts the icons satisfying
the prompted set relation.

## Scene And Query
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

Scalar annotation checked: not applicable. The count can have zero or multiple
visual witnesses, so `bbox_set` is the stable annotation schema.

## Notes
Exact matches are defined over icon type, color, size, and rotation. Added and
missing identities are sampled distinctly so panel membership is unambiguous.
Render metadata records panel-title text legibility.
