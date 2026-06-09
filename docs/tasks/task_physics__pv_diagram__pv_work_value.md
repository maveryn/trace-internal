# `task_physics__pv_diagram__pv_work_value`

## Summary
- Domain: `physics`
- Scene id: `pv_diagram`
- Implementation task group: `thermodynamics`
- Implementation source: `trace/tasks/physics/thermodynamics/pv_diagram.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__pv_diagram__pv_work_value` -> `task_physics__pv_diagram__pv_work_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes signed integer work from a highlighted PV process using pressure times volume change.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `work_value` | `pressure * (final_volume - initial_volume); scene=pv_diagram; scope=pv_work_value; query_branch=work_value` |

## Program Metadata
- Program signatures: `physics.pv_work_value`
- Base program contract: `pressure * (final_volume - initial_volume); scene=pv_diagram; scope=pv_work_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `final_volume`: semantic_role; allowed `visible_final_volume`; source `program_schema_concrete`
  - `initial_volume`: semantic_role; allowed `visible_initial_volume`; source `program_schema_concrete`
  - `pressure`: semantic_role; allowed `visible_process_pressure`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `work_value`

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
- Task review artifacts: `review/task-reviews/physics/pv_diagram/task_physics__pv_diagram__pv_work_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
