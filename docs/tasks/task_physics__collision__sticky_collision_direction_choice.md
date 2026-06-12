# `task_physics__collision__sticky_collision_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/sticky_collision.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__collision__sticky_collision_direction_choice` -> `task_physics__collision__sticky_collision_direction_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the final direction of two perpendicular pucks after a sticky collision using conserved momentum.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `direction_choice` | `option_letter(direction(momentum_sum(pucks_a_b), mode=final_sticky_velocity)); scene=collision; scope=sticky_collision_direction_choice; query_branch=direction_choice` |

## Program Metadata
- Program signatures: `physics.momentum_direction_choice`
- Base program contract: `option_letter(direction(momentum_sum(pucks_a_b), mode=final_sticky_velocity)); scene=collision; scope=sticky_collision_direction_choice`
- Parameter axes: `fixed_query`
- Arguments:
  - `final_sticky_velocity`: semantic_role; allowed `velocity_after_sticky_collision`; source `program_schema_concrete`
  - `pucks_a_b`: semantic_role; allowed `visible_input_pucks_A_B`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `direction_choice`

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
- Task review artifacts: `review/task-reviews/physics/collision/task_physics__collision__sticky_collision_direction_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
