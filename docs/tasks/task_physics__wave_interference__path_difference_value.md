# `task_physics__wave_interference__path_difference_value`

## Summary
- Domain: `physics`
- Scene id: `wave_interference`
- Implementation task group: `waves`
- Implementation source: `trace/tasks/physics/waves/interference_tank.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__wave_interference__path_difference_value` -> `task_physics__wave_interference__path_difference_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the absolute path difference from two sources to a marked point in lambda/2 steps.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `path_difference_value` | `abs(distance(source_s1, point_p) - distance(source_s2, point_p)) / lambda_half_step; scene=wave_interference; scope=path_difference_value` |

## Program Metadata
- Program signatures: `physics.wave_path_difference_value`
- Base program contract: `abs(distance(source_s1, point_p) - distance(source_s2, point_p)) / lambda_half_step; scene=wave_interference; scope=path_difference_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `lambda_half_step`: semantic_role; allowed `visible_lambda_over_two_unit`; source `program_schema_concrete`
  - `point_p`: semantic_role; allowed `visible_point_P`; source `program_schema_concrete`
  - `source_s1`: semantic_role; allowed `visible_source_S1`; source `program_schema_concrete`
  - `source_s2`: semantic_role; allowed `visible_source_S2`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `path_difference_value`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is an exact integer produced by the symbolic physics construction.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; each key maps to the minimal final-image pixel box for that role.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/wave_interference/task_physics__wave_interference__path_difference_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
