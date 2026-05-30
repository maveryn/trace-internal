# task_illustrations__object_field__object_type_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `object_field`
- task_group: `counting`
- task: `type_count`
- module: `trace/tasks/illustrations/counting/type_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a mixed-object illustration canvas with repeated object types,
multiple illustration styles, and non-query distractor objects.

The task records `query_id=type_count`.
The query asks how many objects of a named type are present.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of instances of the queried object type

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted object instance
- evidence boxes are sorted deterministically by rendered position
- `bbox_set` is intentional: witnesses are homogeneous counted object
  instances, so no keyed role binding is needed.

## Trace Contract
- `scene_ir.entities` contains object entities with type, style, placement, and
  semantic part metadata.
- `render_map.object_bboxes_px` stores object bboxes.
- `render_map.counted_object_ids`, `witness_symbolic.counted_object_ids`, and
  `projected_evidence.bbox_set` are derived from the same object records.

## Prompt Contract
- `scene_key = mixed_object_canvas`
- `task_key = type_count_task`
- `query_id = type_count`
- prompts ask for the count of a named object type
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/object_field/scene_review.xlsx`.
- Solve-rate calibration remains pending.
