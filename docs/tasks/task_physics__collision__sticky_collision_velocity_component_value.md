# `task_physics__collision__sticky_collision_velocity_component_value`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/sticky_collision.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__collision__sticky_collision_velocity_component_value` -> `task_physics__collision__sticky_collision_velocity_component_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes one signed velocity component of the combined puck after a sticky collision.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `velocity_component` | `component(final_velocity(momentum_sum(pucks_a_b), combined_mass), axis=component_axis); scene=collision; scope=sticky_collision_velocity_component_value; query_branch=velocity_component` |

## Program Metadata
- Program signatures: `physics.momentum_component_value`
- Base program contract: `component(final_velocity(momentum_sum(pucks_a_b), combined_mass), axis=component_axis); scene=collision; scope=sticky_collision_velocity_component_value`
- Parameter axes: `component_axis`
- Arguments:
  - `combined_mass`: semantic_role; allowed `mass_A_plus_mass_B`; source `program_schema_concrete`
  - `component_axis`: semantic_role; allowed `x`, `y`; source `program_schema_concrete`
  - `pucks_a_b`: semantic_role; allowed `visible_input_pucks_A_B`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `velocity_component`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is an exact integer produced by the symbolic physics construction.

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
- Task review artifacts: `review/task-reviews/physics/collision/task_physics__collision__sticky_collision_velocity_component_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
