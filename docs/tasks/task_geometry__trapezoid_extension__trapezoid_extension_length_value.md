# `task_geometry__trapezoid_extension__trapezoid_extension_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `trapezoid_extension`
4. Public query id: `default`
5. Query ids: `extension_from_parallelogram_area`, `extension_from_parallelogram_perimeter`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_trapezoid_extension_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer the missing dashed extension length `BE` after completing a solid
trapezoid into a larger parallelogram. Query ids either derive the
completed parallelogram base from its area and height, or from its perimeter
and slanted side length. Answers are numeric integers.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the
target length cue, followed by the original trapezoid, the dashed completion,
and the visible supporting labels. Verifier evidence is projected from the
same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/trapezoid_extension.py`
