# `task_geometry__triangle_relations__right_triangle_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query variant: `default`
5. Query id: one of `angle_from_opposite_adjacent`, `angle_from_opposite_hypotenuse`, `angle_from_adjacent_hypotenuse`, or `angle_of_elevation_from_height_and_distance`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_right_triangle_trig_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute a marked acute angle or angle of elevation from two visible right-triangle side labels using inverse trigonometry. Answers are in degrees rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over the marked angle cue and the visible side-label boxes needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/right_triangle_trig.py`
