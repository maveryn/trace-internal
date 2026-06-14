# `task_icons__reference_canvas__reference_metric_relation_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- scene_id: `counting`
- module: `trace/tasks/icons/reference_canvas/reference_metric_relation_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders a Reference icon and a Scene panel, then asks how many Scene icons
satisfy one predicate relative to the Reference.

Query ids:
- `match_type`
- `match_color`
- `match_rotation`
- `match_type_color_rotation`
- `size_smaller`
- `size_larger`

Answer schema: integer.
Annotation schema: `bbox_set` over counted Scene icon boxes only.

## Notes
The reference icon bbox, sampled sizes, colors, rotations, and predicate branch
are retained in trace metadata but are not part of user-facing annotation.

Renderer metadata records sampled palette/style, panel-header text-legibility
metadata, and per-icon noise edits. Size branches share this public task id and
keep their concrete branch in `query_id`.
