# task_illustrations__indoor_room__container_object_count

Status: accepted after qwen25vl7b solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `indoor_room`
- task_group: `counting`
- task: `container_object_count`
- module: `trace/tasks/illustrations/counting/container_object_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders an indoor room with furniture, small objects, and visible
containers such as baskets, boxes, or drawers. The queried container is outlined
in blue to remove container-identity ambiguity.

The public task uses `query_variant=default` and records
`query_id=container_object_count`. The query asks how many objects are inside a
blue-outlined named container.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of visible objects inside the blue-outlined queried
  container
- generated calibration support is `0..4`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted object inside the container
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains indoor furniture, containers, small objects, and
  decor.
- `render_map.container_bboxes_px` stores container bboxes.
- `render_map.object_bboxes_px` stores small-object bboxes.
- `render_map.counted_object_ids`, `witness_symbolic.counted_object_ids`, and
  `projected_evidence.bbox_set` are derived from the same object/container
  records.

## Prompt Contract
- `scene_key = indoor_room_canvas`
- `task_key = container_object_count_task`
- `query_key = container_object_count`
- prompts ask for objects inside the named container
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
