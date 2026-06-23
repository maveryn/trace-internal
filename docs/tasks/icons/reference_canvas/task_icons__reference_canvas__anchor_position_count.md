# `task_icons__reference_canvas__anchor_position_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- module: `trace/tasks/icons/reference_canvas/anchor_position_count.py`
- prompt bundle: `icons_reference_canvas_v1`

## Program Contract
`count.reference_icon_anchor_spatial_predicate(scene=reference_canvas, scope=scene_panel_candidate_icons, reference=left_panel_reference_icon, anchor=marked_scene_icon, predicates=left_of_anchor|right_of_anchor|above_anchor|below_anchor, output=count)`

Renders a Reference icon and a Scene panel with one marked Anchor icon, then
asks for an integer count of Scene candidate icons that match the Reference type
and lie on the requested side of the Anchor.

Supported `query_id`: `left_of_anchor`, `right_of_anchor`, `above_anchor`, `below_anchor`.

Answer schema: integer.
Annotation schema: `bbox_set` over counted Scene candidate icon boxes only.

## Notes
The Reference and Anchor boxes are retained in trace metadata but are not part
of user-facing annotation. The Anchor icon itself is not part of the counted
candidate set.
