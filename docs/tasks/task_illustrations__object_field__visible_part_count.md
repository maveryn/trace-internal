# task_illustrations__object_field__visible_part_count

Status: pending fresh v0 task review and solve-rate calibration.

## Identity
- domain: `illustrations`
- scene_id: `object_field`
- task_group: `counting`
- task: `visible_part_count`
- module: `trace/tasks/illustrations/counting/visible_part_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a mixed canvas of recognizable synthetic objects. Object
families include animals, vehicles, and household/tool objects. The configured
scene uses `6..9` objects and records semantic part bboxes for visible doors,
eyes, handles, tails, and wings.

The task records
`query_id=visible_part_count`. The queried part kind is recorded in trace
metadata as `part_kind`.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of visible queried parts rendered in the image
- configured answer support is `1..6`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted visible part
- evidence boxes are sorted deterministically by rendered position

## Trace Contract
- `scene_ir.entities` contains one `illustration_object` entity per object and
  one `illustration_part` entity per visible semantic part.
- `render_map.object_bboxes_px` stores object bboxes by object id.
- `render_map.part_bboxes_px` stores visible part bboxes by part id.
- `render_map.counted_part_ids`, `witness_symbolic.counted_part_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered part records.

## Prompt Contract
- `scene_key = mixed_object_canvas`
- `task_key = visible_part_count_task`
- `query_id = visible_part_count`
- prompts ask for a visible part count and do not mention canonical real-world
  object priors
- answer-only and answer+evidence modes both include contract-valid JSON
  examples
