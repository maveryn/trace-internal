# `task_physics__electrostatic_field__zero_field_point_label`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Implementation task group: `electrostatics`
- Implementation source: `trace/tasks/physics/electrostatics/field_map.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__electrostatic_field__zero_field_point_label` -> `task_physics__electrostatic_field__zero_field_point_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled candidate point where the net electric field is zero for a two-charge setup.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `zero_field_point_label` | `option_letter(select(candidate_points, net_field(charges_q1_q2, candidate_point)=zero_field)); scene=electrostatic_field; scope=zero_field_point_label` |

## Program Metadata
- Program signatures: `physics.electric_zero_field_selection`
- Base program contract: `option_letter(select(candidate_points, net_field(charges_q1_q2, candidate_point)=zero_field)); scene=electrostatic_field; scope=zero_field_point_label`
- Parameter axes: `fixed_query`
- Arguments:
  - `candidate_point`: semantic_role; allowed `sampled_candidate_point`; source `program_schema_concrete`
  - `candidate_points`: semantic_role; allowed `visible_candidate_points`; source `program_schema_concrete`
  - `charges_q1_q2`: semantic_role; allowed `fixed_same_sign_charge_pair`; source `program_schema_concrete`
  - `zero_field`: semantic_role; allowed `zero_field`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `zero_field_point_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_point_map`
- Generator `annotation_gt.type`: `keyed_point_map`
- Annotation is keyed because point witnesses have distinct roles; each key maps to the final-image pixel point for that role.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/electrostatic_field/task_physics__electrostatic_field__zero_field_point_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
