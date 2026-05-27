# `task_geometry__paper_fold__paper_fold_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `paper_fold`
4. Public query id: `default`
5. Query id: `fold_angle_from_total_label`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_paper_fold_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute a marked angle in a folded-paper corner diagram. The visible crease bisects the marked fold angle, so `x` is one half of the visible total angle label. Answers are numeric angle measures in degrees rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the target `x` angle cue followed by the supporting visible angle label. Verifier evidence is projected from the same generated fold geometry used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/paper_fold_measurement.py`
