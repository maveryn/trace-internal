# task_illustrations__park_playground__person_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `park_playground`
- task_group: `counting`
- task: `park_person_count`
- module: `trace/tasks/illustrations/counting/park_person_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic park/playground with people, equipment, paths,
zones, and decor.

Query ids:

- `sitting_person_count`
- `walking_person_count`
- `standing_person_count`
- `playing_ball_person_count`
- `playground_area_person_count`
- `picnic_area_person_count`
- `garden_area_person_count`
- `person_using_slide_count`
- `person_using_swing_set_count`
- `person_using_seesaw_count`

## Answer Contract
- `answer_gt.type = integer`
- value is the count requested by the selected `query_id`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox around each counted person
- `bbox_set` is intentional: each query asks for an unordered homogeneous set
  of counted people, so no keyed role binding is needed.

## Trace Contract
- `query_spec.task_id` is this public task id.
- `query_spec.branch_id` records the private branch generator used for the
  selected query.
- `query_spec.params.merged_query_probabilities` records query
  sampling support.
- Branch-specific render maps and witness fields are preserved.

## Prompt Contract
- `scene_key = park_playground_canvas`
- `query_id` is the selected branch
- branch-specific task keys from `illustrations_counting_v0` are reused

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/park_playground/scene_review.xlsx`.
- Person placement fallback is clamped inside the canvas and preserves requested
  zone/equipment context before evidence projection.
- Solve-rate calibration remains pending.
