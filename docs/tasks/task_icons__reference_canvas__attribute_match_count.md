# `task_icons__reference_canvas__attribute_match_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- task_group: `counting`
- module: `trace/tasks/icons/counting/reference_match_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders a Reference icon and a Scene panel, then asks how many Scene icons match
the Reference under the selected attribute predicate.

Query ids:
- `match_type`
- `match_color`
- `match_rotation`
- `match_type_color_rotation`

Answer schema: integer.
Evidence schema: `bbox_set` over counted Scene icon boxes only.

## Notes
The reference icon bbox is retained in trace metadata but is not part of the
user-facing evidence.
