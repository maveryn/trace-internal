# task_illustrations__transit_terminal__entity_location_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Identity
- domain: `illustrations`
- scene_id: `transit_terminal`
- task_group: `counting`
- task: `terminal_entity_location_count`
- module: `trace/tasks/illustrations/counting/terminal_entity_location_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic transit terminal with labeled boarding areas,
service points, people, luggage, and terminal decor.

Query ids:

- `person_in_boarding_area_count`
- `luggage_in_boarding_area_count`
- `person_in_queue_count`

The named boarding area, luggage type, and service point are sampled as
instance parameters rather than separate query ids.

## Answer Contract
- `answer_gt.type = integer`
- value is the count requested by the selected `query_id`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- person queries return one bbox around each counted person
- luggage queries return one bbox around each counted luggage item
- `bbox_set` is intentional: each query asks for an unordered homogeneous set
  of counted people or luggage, so no keyed role binding is needed.

## Trace Contract
- `query_spec.task_id` is this public task id.
- `query_spec.branch_id` records the private branch generator used for the
  selected query.
- `query_spec.params.merged_query_probabilities` records query
  sampling support.
- Branch-specific render maps and witness fields are preserved.
- Raw sampled counts, target ids, target area/service/luggage metadata, and
  source layout diagnostics stay in trace metadata. Public complexity
  components use normalized numeric load values only.

## Prompt Contract
- `scene_key = transit_terminal_canvas`
- `query_id` is the selected branch
- branch-specific task keys from `illustrations_counting_v0` are reused

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/transit_terminal/scene_review.xlsx`.
- Query ids were refactored on 2026-05-28 so area/type/service choices are
  internal sampled parameters under three reasoning-pattern query ids.
- Transit person placement now clamps random and fallback placements inside the
  requested semantic boarding area before evidence projection.
- In luggage-count scenes, background people are placed in the concourse and
  standalone luggage avoids person bboxes, preventing backpacks/suitcases from
  reading as worn or attached to a person.
- Review sidecar audit covered 100 instances across all 3 query ids with zero
  evidence/answer/location contract errors.
- Solve-rate calibration remains pending.
