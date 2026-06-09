# `task_physics__pulley__pulley_mechanical_advantage`

## Summary
- Domain: `physics`
- Scene id: `pulley`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/pulley_mechanical_advantage.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__pulley__pulley_mechanical_advantage` -> `task_physics__pulley__pulley_mechanical_advantage`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Solves an ideal pulley force relation from visible support strands and known/unknown force labels.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `force_relation` | `solve_ideal_pulley(load_force, effort_force, support_strand_count, unknown_slot); scene=pulley; scope=pulley_mechanical_advantage; query_branch=force_relation` |

## Program Metadata
- Program signatures: `physics.pulley_force_solve`
- Base program contract: `solve_ideal_pulley(load_force, effort_force, support_strand_count, unknown_slot); scene=pulley; scope=pulley_mechanical_advantage`
- Parameter axes: `unknown_slot`
- Arguments:
  - `effort_force`: semantic_role; allowed `visible_or_unknown_effort_force`; source `program_schema_concrete`
  - `load_force`: semantic_role; allowed `visible_or_unknown_load_force`; source `program_schema_concrete`
  - `support_strand_count`: semantic_role; allowed `counted_full_supporting_strands`; source `program_schema_concrete`
  - `unknown_slot`: semantic_role; allowed `effort_force`, `load_force`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `force_relation`

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
- Task review artifacts: `review/task-reviews/physics/pulley/task_physics__pulley__pulley_mechanical_advantage/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
