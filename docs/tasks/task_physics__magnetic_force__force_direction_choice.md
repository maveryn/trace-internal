# `task_physics__magnetic_force__force_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `magnetic_force`
- Implementation task group: `magnetism`
- Implementation source: `trace/tasks/physics/magnetism/force_field.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_physics__magnetic_force__force_direction_choice` -> `task_physics__magnetic_force__force_direction_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the Lorentz-force direction from visible magnetic-field orientation, charge sign, and velocity direction.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `force_direction_choice` | `option_letter(direction(charge_sign * cross_product(velocity_vector, magnetic_field_orientation))); scene=magnetic_force; scope=force_direction_choice` |

## Program Metadata
- Program signatures: `physics.lorentz_force_direction_choice`
- Base program contract: `option_letter(direction(charge_sign * cross_product(velocity_vector, magnetic_field_orientation))); scene=magnetic_force; scope=force_direction_choice`
- Parameter axes: `charge_sign`, `magnetic_field_orientation`
- Arguments:
  - `charge_sign`: semantic_role; allowed `negative_charge`, `positive_charge`; source `program_schema_concrete`
  - `magnetic_field_orientation`: semantic_role; allowed `into_page`, `out_of_page`; source `program_schema_concrete`
  - `velocity_vector`: semantic_role; allowed `visible_velocity_arrow`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `force_direction_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

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
- Task review artifacts: `review/task-reviews/physics/magnetic_force/task_physics__magnetic_force__force_direction_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
