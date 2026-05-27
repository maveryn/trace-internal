# `task_geometry__trapezoid_extension__trapezoid_extension_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `trapezoid_extension`
4. Public query id: `default`
5. Query ids: `trapezoid_area_from_bases_and_height`, `trapezoid_area_from_extension_and_height`, `trapezoid_area_from_parallelogram_area`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_trapezoid_extension_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer the area of the original trapezoid in a dashed
parallelogram-completion diagram. Query ids either use the visible top
base, bottom base, and height directly, derive the bottom base from the dashed
extension, or derive the bottom base from the completed parallelogram area.
Answers are numeric integers.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the
target area cue, followed by the original trapezoid, the dashed completion,
and the visible supporting labels. Verifier evidence is projected from the
same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/trapezoid_extension.py`
