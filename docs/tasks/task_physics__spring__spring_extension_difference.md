# `task_physics__spring__spring_extension_difference`

## Summary
- Domain: `physics`
- Scene id: `spring`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/spring_extension.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__spring__spring_extension_difference` -> `task_physics__spring__spring_extension_difference`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the absolute difference between two visible spring-extension markers.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `extension_difference` | `abs(extension_a - extension_b); scene=spring; scope=spring_extension_difference; query_branch=extension_difference` |

## Program Metadata
- Program signatures: `physics.extension_difference_value`
- Base program contract: `abs(extension_a - extension_b); scene=spring; scope=spring_extension_difference`
- Parameter axes: `fixed_query`
- Arguments:
  - `extension_a`: semantic_role; allowed `first_visible_extension_marker`; source `program_schema_concrete`
  - `extension_b`: semantic_role; allowed `second_visible_extension_marker`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `extension_difference`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is an exact integer produced by the symbolic physics construction.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set | unordered`
- Annotation is an unordered set of final-image pixel boxes over the minimal queried visual witnesses.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/spring/task_physics__spring__spring_extension_difference/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
