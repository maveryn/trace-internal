# task_illustrations__park_playground__playground_equipment_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `park_playground`
- task_group: `counting`
- task: `playground_equipment_count`
- module: `trace/tasks/illustrations/counting/playground_equipment_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic park/playground with people, paths, zones, and
semantic playground equipment.

Query ids:

- `slide_count`
- `swing_set_count`
- `seesaw_count`
- `climbing_frame_count`

Each variant asks for the count of one equipment type.

## Answer Contract
- `answer_gt.type = integer`
- value is the number of rendered equipment items whose equipment type matches
  the query

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox around each counted equipment item
- `bbox_set` is intentional: each query asks for an unordered homogeneous set
  of counted equipment items, so no keyed role binding is needed.

## Trace Contract
- `render_map.decor_bboxes_px` stores final decor and equipment bboxes.
- `execution_trace.decor` records equipment ids, equipment type, and bbox.
- `render_map.counted_equipment_ids`,
  `witness_symbolic.counted_equipment_ids`, and
  `projected_evidence.bbox_set` are derived from the same rendered equipment
  records.

## Prompt Contract
- `scene_key = park_playground_canvas`
- `task_key = playground_equipment_count_task`
- `query_id` is one of the four equipment-count branches above
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/park_playground/scene_review.xlsx`.
- Solve-rate calibration remains pending.
