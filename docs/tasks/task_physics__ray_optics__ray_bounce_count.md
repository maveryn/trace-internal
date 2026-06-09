# `task_physics__ray_optics__ray_bounce_count`

## Summary
- Domain: `physics`
- Scene id: `ray_optics`
- Implementation task group: `optics`
- Implementation source: `trace/tasks/physics/optics/ray_trace.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__ray_optics__ray_bounce_count` -> `task_physics__ray_optics__ray_bounce_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts reflection events along the hidden ray path implied by visible mirrors and the initial ray direction.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `bounce_count` | `count(reflection_points(hidden_ray_path)); scene=ray_optics; scope=ray_bounce_count; query_branch=bounce_count` |

## Program Metadata
- Program signatures: `physics.ray_path_event_count`
- Base program contract: `count(reflection_points(hidden_ray_path)); scene=ray_optics; scope=ray_bounce_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `hidden_ray_path`: semantic_role; allowed `trace_solved_ray_path`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `bounce_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a non-negative integer count of the queried visual events or targets.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set | unordered`
- Annotation is an unordered set of final-image pixel points over the queried event/target centers.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/ray_optics/task_physics__ray_optics__ray_bounce_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
