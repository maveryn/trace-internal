# `task_physics__spring__spring_missing_value`

## Summary
- Domain: `physics`
- Scene id: `spring`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/spring_extension.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__spring__spring_missing_value` -> `task_physics__spring__spring_missing_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Solves a missing weight or extension for identical springs using a visible reference pair.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `missing_value` | `solve_hooke_ratio(reference_weight, reference_extension, query_weight, query_extension, unknown_slot); scene=spring; scope=spring_missing_value; query_branch=missing_value` |

## Program Metadata
- Program signatures: `physics.hooke_law_solve`
- Base program contract: `solve_hooke_ratio(reference_weight, reference_extension, query_weight, query_extension, unknown_slot); scene=spring; scope=spring_missing_value`
- Parameter axes: `unknown_slot`
- Arguments:
  - `query_extension`: semantic_role; allowed `right_spring_extension`; source `program_schema_concrete`
  - `query_weight`: semantic_role; allowed `right_spring_weight`; source `program_schema_concrete`
  - `reference_extension`: semantic_role; allowed `reference_spring_extension`; source `program_schema_concrete`
  - `reference_weight`: semantic_role; allowed `reference_spring_weight`; source `program_schema_concrete`
  - `unknown_slot`: semantic_role; allowed `missing_extension`, `missing_weight`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `missing_value`

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
- Task review artifacts: `review/task-reviews/physics/spring/task_physics__spring__spring_missing_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
