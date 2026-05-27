# task_illustrations__environment__lit_window_count

Status: accepted after qwen25vl7b solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `environment`
- task_group: `counting`
- task: `building_window_count`
- module: `trace/tasks/illustrations/counting/building_window_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders an illustrated street or canal-city environment with building
facades and visible lit/unlit windows.

The public task uses `query_variant=default` and records
`query_id=building_window_count`. The query asks how many lit windows are shown
on the buildings.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of lit building windows

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted lit window
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains buildings, windows, environment features, and
  non-query scene decor.
- `render_map.window_bboxes_px` stores visible building-window bboxes.
- `render_map.counted_window_ids`, `witness_symbolic.counted_window_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered windows.

## Prompt Contract
- `scene_key = environment_object_canvas`
- `task_key = building_window_count_task`
- `query_key = building_window_count`
- prompts ask for lit windows on buildings
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
