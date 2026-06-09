# `task_physics__orbital_motion__focus_location_label`

## Summary
- Domain: `physics`
- Scene id: `orbital_motion`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/orbital_motion.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__orbital_motion__focus_location_label` -> `task_physics__orbital_motion__focus_location_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled point that can be the Sun at a focus of an elliptical orbit.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `sun_focus_label` | `option_letter(select(candidate_points, point_is_focus_of_ellipse)); scene=orbital_motion; scope=focus_location_label; query_branch=sun_focus_label` |

## Program Metadata
- Program signatures: `physics.orbital_focus_location_label`
- Base program contract: `option_letter(select(candidate_points, point_is_focus_of_ellipse)); scene=orbital_motion; scope=focus_location_label`
- Parameter axes: `fixed_query`
- Arguments:
  - `candidate_points`: semantic_role; allowed `visible_labeled_candidate_points`; source `program_schema_concrete`
  - `ellipse_geometry`: semantic_role; allowed `visible_ellipse_center_and_major_axis`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `sun_focus_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible candidate label.

## Annotation Contract
- Annotation schema: `keyed_point_map`
- Generator `annotation_gt.type`: `keyed_point_map`
- Annotation is keyed because point witnesses have distinct roles; keys include `center`, `selected_focus`, `major_axis_endpoint_1`, and `major_axis_endpoint_2`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/orbital_motion/task_physics__orbital_motion__focus_location_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
