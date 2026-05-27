# task_illustrations__indoor_room__surface_object_count

Status: accepted after qwen25vl7b solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `indoor_room`
- task_group: `counting`
- task: `object_type_on_surface_count`
- module: `trace/tasks/illustrations/counting/object_type_on_surface_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders an indoor room with furniture surfaces and many small objects
placed on or away from those surfaces.

The public task uses `query_variant=default` and records
`query_id=object_type_on_surface_count`. The query asks how many objects of a
named type are on a named surface such as a table, shelf, or counter.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of queried object instances on the queried surface

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted object
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains indoor furniture, surfaces, small objects, and
  decor.
- `render_map.surface_bboxes_px` stores surface bboxes.
- `render_map.object_bboxes_px` stores small-object bboxes.
- `render_map.counted_object_ids`, `witness_symbolic.counted_object_ids`, and
  `projected_evidence.bbox_set` are derived from the same object/surface
  records.

## Prompt Contract
- `scene_key = indoor_room_canvas`
- `task_key = object_type_on_surface_count_task`
- `query_key = object_type_on_surface_count`
- prompts ask for named objects on the named surface
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
