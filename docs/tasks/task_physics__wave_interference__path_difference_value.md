# `task_physics__wave_interference__path_difference_value`

- Domain: `physics`
- Scene id: `wave_interference`
- Task group: `waves`
- Query id: `path_difference_value`
- Public query id: `default`
- Answer type: `integer`
- Evidence type: `bbox_set`

## Summary

Shows the same two-source ripple-tank scene with a highlighted point `P` and labeled dashed guide paths from `S1` and `S2` to `P`. The task asks for the absolute path difference counted in `lambda/2` steps.

## Prompt Contract

Prompt bundle: `physics_waves_v0`; scene key: `wave_interference_tank`; task key: `wave_interference_tank_query`; query key: `path_difference_value`.

Outputs `query_id="path_difference_value"`. The trace records source phase relation, point `P` coordinates, exact source-to-point distances in `lambda/2` steps, path-difference answer, and evidence entity ids.

## Evidence Contract

Evidence is one bbox around the two labeled source-to-`P` guide paths and point `P`, including the relevant source markers. Wavefront rings and grid lines are scene context.

## Sampling Notes

- `scene_variant`: `clean_tank|grid_tank|lab_sheet`
- `phase_relation`: `in_phase|opposite_phase`
- `path_difference_step_support`: integer answers `1..4`
