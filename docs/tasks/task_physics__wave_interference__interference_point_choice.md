# `task_physics__wave_interference__interference_point_choice`

- Domain: `physics`
- Scene id: `wave_interference`
- Task group: `waves`
- Query id: `interference_point_choice`
- Public query id: `default`
- Answer type: `option_letter`
- Evidence type: `bbox_set`

## Summary

Shows a two-source ripple-tank interference diagram with circular crest/trough wavefronts and labeled candidate points `A-E`. The task asks which point has the requested interference condition.

## Prompt Contract

Prompt bundle: `physics_waves_v0`; scene key: `wave_interference_tank`; task key: `wave_interference_tank_query`; query key: `interference_point_choice`.

Outputs `query_id="interference_point_choice"`. The trace records source phase relation, target condition, candidate point distances from each source in `lambda/2` steps, each point's resolved condition, the correct option letter, and evidence entity ids.

## Evidence Contract

Evidence is one bbox around the correct labeled candidate point. Source markers, wavefront rings, grid lines, and legend text are scene context, not prompt-facing evidence.

## Sampling Notes

- `scene_variant`: `clean_tank|grid_tank|lab_sheet`
- `phase_relation`: `in_phase|opposite_phase`
- `target_condition`: `constructive|destructive`
- Candidate labels `A-E` are balanced as the final answer support.
