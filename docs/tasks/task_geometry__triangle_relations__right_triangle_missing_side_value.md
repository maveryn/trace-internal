# `task_geometry__triangle_relations__right_triangle_missing_side_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query id: `default`
5. Query id: one of `height_from_angle_and_ground`, `ground_from_angle_and_height`, `hypotenuse_from_angle_and_height`, `height_from_angle_and_hypotenuse`, or `ground_from_angle_and_hypotenuse`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_right_triangle_trig_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute a missing right-triangle side from one acute angle and one side label. Branches cover height, ground/run, and hypotenuse-style targets. Answers are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over the unknown-side cue, the marked angle label, and the visible side-label box needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/right_triangle_trig.py`
