# `task_icons__reference_canvas__reference_attribute_match_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- module: `trace/tasks/icons/reference_canvas/reference_attribute_match_count.py`
- prompt bundle: `icons_reference_canvas_v1`

## Program Contract
`count.reference_icon_attribute_predicate(scene=reference_canvas, scope=scene_panel_icons, reference=left_panel_reference_icon, predicates=same_type|same_color|same_rotation|same_type_color_rotation, output=count)`

Renders a Reference icon and a Scene panel, then asks for an integer count of
Scene icons satisfying one attribute predicate relative to the Reference.

Supported `query_id`: `match_type`, `match_color`, `match_rotation`, `match_type_color_rotation`.

Answer schema: integer.
Annotation schema: `bbox_set` over counted Scene icon boxes only.

## Notes
The Reference icon bbox, sampled color, sampled rotation, and sampled icon ids
are retained in trace metadata. Annotation covers only the counted Scene icons.
