# `task_icons__reference_canvas__reference_metric_relation_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- module: `trace/tasks/icons/reference_canvas/reference_metric_relation_count.py`
- prompt bundle: `icons_reference_canvas_v1`

## Program Contract
`count.reference_icon_metric_predicate(scene=reference_canvas, scope=scene_panel_icons, reference=left_panel_reference_icon, metric=nominal_size, predicates=smaller_than_reference|larger_than_reference, output=count)`

Renders a Reference icon and a Scene panel, then asks for an integer count of
Scene icons whose nominal size is smaller or larger than the Reference.

Supported `query_id`: `size_smaller`, `size_larger`.

Answer schema: integer.
Annotation schema: `bbox_set` over counted Scene icon boxes only.

## Notes
The concrete Reference size, per-icon nominal sizes, and minimum size delta are
retained in trace metadata. Annotation covers only the counted Scene icons.
