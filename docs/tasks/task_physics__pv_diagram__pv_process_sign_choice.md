# `task_physics__pv_diagram__pv_process_sign_choice`

## Summary
- Domain: `physics`
- Scene id: `pv_diagram`
- Implementation task group: `thermodynamics`
- Implementation source: `trace/tasks/physics/thermodynamics/pv_diagram.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__pv_diagram__pv_process_sign_choice` -> `task_physics__pv_diagram__pv_process_sign_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the process option whose volume-change sign matches the requested PV-process sign.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `process_sign_choice` | `option_letter(select(candidate_processes, sign(volume_change(process))=target_sign)); scene=pv_diagram; scope=pv_process_sign_choice; query_branch=process_sign_choice` |

## Program Metadata
- Program signatures: `physics.pv_process_sign_choice`
- Base program contract: `option_letter(select(candidate_processes, sign(volume_change(process))=target_sign)); scene=pv_diagram; scope=pv_process_sign_choice`
- Parameter axes: `target_sign`
- Arguments:
  - `candidate_processes`: semantic_role; allowed `visible_mini_pv_processes`; source `program_schema_concrete`
  - `process`: semantic_role; allowed `candidate_pv_process`; source `program_schema_concrete`
  - `target_sign`: semantic_role; allowed `negative`, `positive`, `zero`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `process_sign_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

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
- Task review artifacts: `review/task-reviews/physics/pv_diagram/task_physics__pv_diagram__pv_process_sign_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
