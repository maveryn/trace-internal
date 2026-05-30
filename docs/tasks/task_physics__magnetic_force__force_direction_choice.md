# `task_physics__magnetic_force__force_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `magnetic_force`
- Task group: `magnetism`
- Query id: `force_direction_choice`
- Answer type: `option_letter`
- Evidence type: `keyed_bbox_map`

## Contract
The image shows a charged particle moving through a uniform magnetic field drawn with into-page or out-of-page symbols. The particle has a visible velocity vector, and the side panel contains eight labeled candidate force arrows. The calibrated public mix uses the gridded field-panel scene, larger particle signs and candidate arrows, and six active correct-answer letters while retaining all eight candidates as visible options.

The solver must use the charge sign, velocity direction, and magnetic-field orientation to choose the candidate arrow matching `F=q v x B`.

## Evidence
Prompt-facing evidence is a `keyed_bbox_map` over the input witnesses needed to derive the force direction:

- `field_orientation`: bounding box around the magnetic-field orientation label
- `charge`: bounding box around the charged particle marker/sign
- `velocity`: bounding box around the visible velocity vector

## Prompt And Trace
Prompt bundle: `physics_magnetism_v0`; scene key: `magnetic_force_field`; task key: `magnetic_force_field_query`; query key: `force_direction_choice`.

Outputs `query_id="force_direction_choice"`. The trace records the field orientation, charge sign, velocity direction, resolved force direction, option-arrow directions, selected option letter, and evidence entity ids. Candidate arrows are answer options and are not prompt-facing evidence.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized magnetic-force scenario.
