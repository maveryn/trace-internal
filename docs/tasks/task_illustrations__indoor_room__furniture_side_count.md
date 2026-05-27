# task_illustrations__indoor_room__furniture_side_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `indoor_room`
- task_group: `relation`
- task: `furniture_side_count`
- module: `trace/tasks/illustrations/relation/furniture_side_count.py`
- prompt bundle: `prompts/illustrations/relation/illustrations_relation_v0.json`

## Scene And Query
The task renders an indoor room with furniture and small objects arranged around
the furniture.

The task records
`query_id=furniture_side_count`. The query asks how many objects of a named type
are left, right, above, or below a named furniture item. Current sampling
use answer support `1..6`.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of queried object instances satisfying the requested
  spatial relation to the furniture
- configured answer support is `1..6`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted object
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains furniture, small objects, and indoor decor.
- `render_map.furniture_bboxes_px` stores furniture bboxes.
- `render_map.object_bboxes_px` stores small-object bboxes.
- `render_map.counted_object_ids`, `witness_symbolic.counted_object_ids`, and
  `projected_evidence.bbox_set` are derived from the same placement records.

## Prompt Contract
- `scene_key = indoor_room_canvas`
- `task_key = furniture_side_count_task`
- `query_id = furniture_side_count`
- prompts ask for named objects in the requested relation to furniture
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
