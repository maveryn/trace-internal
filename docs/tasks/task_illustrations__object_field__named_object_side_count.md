# task_illustrations__object_field__named_object_side_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `object_field`
- task_group: `relation`
- task: `named_object_side_count`
- module: `trace/tasks/illustrations/relation/named_object_side_count.py`
- prompt bundle: `prompts/illustrations/relation/illustrations_relation_v0.json`

## Scene And Query
The task renders a mixed-object illustration canvas with exactly one reference
object of the named type and multiple candidate objects around it.

The task records
`query_id=named_object_side_count`. The query asks how many objects are left,
right, above, or below the only object of the named reference type.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of objects satisfying the requested spatial relation to
  the unique reference object

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted object
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains the unique reference object and candidate object
  entities.
- `render_map.object_bboxes_px` stores all object bboxes.
- `render_map.reference_object_id` identifies the unique reference object.
- `render_map.counted_object_ids`, `witness_symbolic.counted_object_ids`, and
  `projected_evidence.bbox_set` are derived from the same placement records.

## Prompt Contract
- `scene_key = mixed_object_canvas`
- `task_key = named_object_side_count_task`
- `query_id = named_object_side_count`
- prompts ask for objects in the requested relation to the only named reference
  object
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
