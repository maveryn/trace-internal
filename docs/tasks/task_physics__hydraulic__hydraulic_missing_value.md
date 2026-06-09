# `task_physics__hydraulic__hydraulic_missing_value`

## Summary
- Domain: `physics`
- Scene id: `hydraulic`
- Implementation task group: `fluids`
- Implementation source: `trace/tasks/physics/fluids/hydraulic_missing_value.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__hydraulic__hydraulic_missing_value` -> `task_physics__hydraulic__hydraulic_missing_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Solves a missing force or piston area in a connected hydraulic piston diagram using Pascal law.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `missing_input_area` | `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot); scene=hydraulic; scope=hydraulic_missing_value; query_branch=missing_input_area` |
| `missing_input_force` | `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot); scene=hydraulic; scope=hydraulic_missing_value; query_branch=missing_input_force` |
| `missing_output_force` | `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot); scene=hydraulic; scope=hydraulic_missing_value; query_branch=missing_output_force` |
| `missing_piston_area` | `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot); scene=hydraulic; scope=hydraulic_missing_value; query_branch=missing_piston_area` |

## Program Metadata
- Program signatures: `physics.pascal_law_solve`
- Base program contract: `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot); scene=hydraulic; scope=hydraulic_missing_value`
- Parameter axes: `unknown_slot`
- Arguments:
  - `input_area`: semantic_role; allowed `visible_input_piston_area`; source `program_schema_concrete`
  - `input_force`: semantic_role; allowed `visible_or_unknown_input_force`; source `program_schema_concrete`
  - `output_area`: semantic_role; allowed `visible_or_unknown_output_piston_area`; source `program_schema_concrete`
  - `output_force`: semantic_role; allowed `visible_or_unknown_output_force`; source `program_schema_concrete`
  - `unknown_slot`: semantic_role; allowed `input_area`, `input_force`, `output_area`, `output_force`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `missing_input_area`, `missing_input_force`, `missing_output_force`, `missing_piston_area`

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
- Task review artifacts: `review/task-reviews/physics/hydraulic/task_physics__hydraulic__hydraulic_missing_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
