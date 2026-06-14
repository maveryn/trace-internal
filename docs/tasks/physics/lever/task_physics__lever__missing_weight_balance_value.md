# `task_physics__lever__missing_weight_balance_value`

## Summary
- Domain: `physics`
- Scene id: `lever`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/lever_balance.py`

## Task Contract
Solves the missing weight needed to balance a visible lever using torque equality.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `missing_weight_to_balance` | `solve_torque_balance(left_weight_distance_terms, right_weight_distance_terms, unknown_weight); scene=lever; scope=missing_weight_balance_value; query_branch=missing_weight_to_balance` |

## Program Metadata
- Program signatures: `physics.torque_balance_solve`
- Base program contract: `solve_torque_balance(left_weight_distance_terms, right_weight_distance_terms, unknown_weight); scene=lever; scope=missing_weight_balance_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `left_weight_distance_terms`: semantic_role; allowed `visible_left_weight_distance_terms`; source `program_schema_concrete`
  - `right_weight_distance_terms`: semantic_role; allowed `visible_right_weight_distance_terms`; source `program_schema_concrete`
  - `unknown_weight`: semantic_role; allowed `marked_missing_weight`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `missing_weight_to_balance`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is an exact integer produced by the symbolic physics construction.

## Annotation Contract
- Annotation schema: `keyed_bbox_set_map`
- Generator `annotation_gt.type`: `keyed_bbox_set_map`
- Annotation is keyed because witness groups have distinct roles; each key maps to one or more minimal final-image pixel boxes.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.
