# `task_physics__orbital_motion__orbital_speed_extremum_label`

## Summary
- Domain: `physics`
- Scene id: `orbital_motion`
- Implementation task group: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/orbital_motion.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__orbital_motion__orbital_speed_extremum_label` -> `task_physics__orbital_motion__orbital_speed_extremum_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled orbital position where speed is greatest or least using Sun-at-focus perihelion/aphelion reasoning.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `greatest_speed_position_label` | `option_letter(arg_extreme(candidate_orbit_positions, distance_to_sun_focus, direction=nearest)); scene=orbital_motion; scope=orbital_speed_extremum_label; query_branch=greatest_speed_position_label` |
| `least_speed_position_label` | `option_letter(arg_extreme(candidate_orbit_positions, distance_to_sun_focus, direction=farthest)); scene=orbital_motion; scope=orbital_speed_extremum_label; query_branch=least_speed_position_label` |

## Program Metadata
- Program signatures: `physics.orbital_speed_extremum_label`
- Base program contract: `option_letter(arg_extreme(candidate_orbit_positions, distance_to_sun_focus, direction=speed_extremum)); scene=orbital_motion; scope=orbital_speed_extremum_label`
- Parameter axes: `speed_extremum_direction`
- Arguments:
  - `candidate_orbit_positions`: semantic_role; allowed `visible_labeled_positions_on_orbit`; source `program_schema_concrete`
  - `sun_focus`: semantic_role; allowed `visible_sun_at_focus`; source `program_schema_concrete`
  - `speed_extremum_direction`: semantic_role; allowed `greatest`, `least`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `greatest_speed_position_label`, `least_speed_position_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible candidate label.

## Annotation Contract
- Annotation schema: `keyed_point_map`
- Generator `annotation_gt.type`: `keyed_point_map`
- Annotation is keyed because point witnesses have distinct roles; keys include `sun` and `selected_position`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/orbital_motion/task_physics__orbital_motion__orbital_speed_extremum_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
