# `task_physics__lever__side_torque_value`

## Summary
- Domain: `physics`
- Scene id: `lever`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/lever_balance.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__lever__side_torque_value` -> `task_physics__lever__side_torque_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the total torque from the visible weights on one queried lever side.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `side_torque` | `sum(weight_i * distance_i for weight_i in weights_on_queried_side); scene=lever; scope=side_torque_value; query_branch=side_torque` |

## Program Metadata
- Program signatures: `physics.torque_sum_value`
- Base program contract: `sum(weight_i * distance_i for weight_i in weights_on_queried_side); scene=lever; scope=side_torque_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `distance_i`: semantic_role; allowed `visible_distance_from_fulcrum`; source `program_schema_concrete`
  - `weight_i`: semantic_role; allowed `visible_weight_block`; source `program_schema_concrete`
  - `weights_on_queried_side`: semantic_role; allowed `visible_weights_on_queried_side`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `side_torque`

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
- Task review artifacts: `review/task-reviews/physics/lever/task_physics__lever__side_torque_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
