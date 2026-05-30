# `task_physics__wave_interference__path_difference_value`

- Domain: `physics`
- Scene id: `wave_interference`
- Task group: `waves`
- Query id: `path_difference_value`
- Answer type: `integer`
- Evidence type: `keyed_bbox_map`

## Summary

Shows the same two-source ripple-tank scene with a highlighted point `P` and labeled dashed guide paths from `S1` and `S2` to `P`. The task asks for the absolute path difference counted in `lambda/2` steps.

## Prompt Contract

Prompt bundle: `physics_waves_v0`; scene key: `wave_interference_tank`; task key: `wave_interference_tank_query`; query key: `path_difference_value`.

Outputs `query_id="path_difference_value"`. The trace records source phase relation, point `P` coordinates, exact source-to-point distances in `lambda/2` steps, path-difference answer, evidence entity ids, technical diagram style, font family, whole-tank layout placement, and post-render noise metadata.

## Evidence Contract

Evidence is a `keyed_bbox_map` with keys `S1P` and `S2P`. Each value is a bbox around the corresponding labeled dashed source-to-`P` guide path.

Evidence is projected after the final whole-tank layout offset.

## Rendering

The renderer uses shared `technical_diagram_style` for the outer sheet, tank/grid palette, frame, and post-render noise. It samples one readout font family per tank and applies whole-tank layout placement before computing keyed evidence.

## Sampling Notes

- `scene_variant`: `clean_tank|grid_tank|lab_sheet`
- `phase_relation`: `in_phase|opposite_phase`
- `path_difference_step_support`: integer answers `1..5`
