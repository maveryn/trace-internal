# `task_physics__piston_cylinder__boundary_work_value`

## Summary
- Domain: `physics`
- Scene id: `piston_cylinder`
- Implementation task group: `thermodynamics`
- Implementation source: `trace/tasks/physics/thermodynamics/piston_cylinder.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__piston_cylinder__boundary_work_value` -> `task_physics__piston_cylinder__boundary_work_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes signed constant-pressure boundary work from visible pressure, initial volume, final volume, and process direction in a piston-cylinder diagram.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query variation is limited to narrow operand and renderer parameters inside the same thermodynamic boundary-work program.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `constant_pressure_boundary_work` | `integer(boundary_work_kj(pressure_mpa, final_volume_l - initial_volume_l)); scene=piston_cylinder; scope=boundary_work_value` |

## Program Metadata
- Program signatures: `physics.piston_cylinder_boundary_work`
- Base program contract: `integer(P_MPa * (V_final_L - V_initial_L)); scene=piston_cylinder; scope=boundary_work_value`
- Parameter axes: `pressure_mpa`, `initial_volume_l`, `final_volume_l`, `orientation`
- Arguments:
  - `piston_cylinder`: semantic_role; allowed `visible_initial_and_final_piston_cylinder_apparatus`; source `program_schema_concrete`
  - `initial_state_label`: query_operand; allowed `visible_pressure_and_initial_volume_label`; source `program_schema_concrete`
  - `final_state_label`: query_operand; allowed `visible_pressure_and_final_volume_label`; source `program_schema_concrete`
  - `process_arrow`: query_operand; allowed `visible_initial_to_final_process_arrow`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `constant_pressure_boundary_work`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the signed boundary work in `kJ`, using work done by the gas as positive.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `piston_cylinder`, `initial_state_label`, `final_state_label`, `process_arrow`
- Annotation must mark the minimal visible witnesses needed to compute signed work. It must not mark decorative background grid lines, panel framing, or derived answer text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics thermodynamics prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, pressure, volumes, orientation, gas color, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep pressure and volume labels readable, show a clear initial-to-final process arrow, and avoid zero-work cases in the initial calibrated support.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/piston_cylinder/task_physics__piston_cylinder__boundary_work_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
