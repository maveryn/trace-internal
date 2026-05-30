# `task_icons__reference_canvas__reference_predicate_count`

## Identity
- domain: `icons`
- scene_id: `reference_canvas`
- task_group: `counting`
- module: `trace/tasks/icons/counting/reference_match_count.py`
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
Evidence schema: `bbox_set` over counted Scene icon boxes only.

## Notes
The reference icon bbox, sampled sizes, colors, rotations, and predicate branch
are retained in trace metadata but are not part of user-facing evidence.

Renderer metadata records sampled palette/style, panel-header text-legibility
metadata, and per-icon noise edits. Size branches share this public task id and
keep their concrete branch in `query_id`.

## Current Review Status
Current browser-review sidecars live under
`review/task-reviews/icons/reference_canvas/task_icons__reference_canvas__reference_predicate_count/`.
Public evidence uses the shared icon `bbox_set` payload over counted Scene icons
only. Solve-rate status is tracked in `review/calibration_sweep_status.json`.
