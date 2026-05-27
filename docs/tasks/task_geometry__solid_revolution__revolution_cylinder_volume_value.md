# `task_geometry__solid_revolution__revolution_cylinder_volume_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_revolution`
4. Public query variant: `default`
5. Query id: `cylinder_volume_from_rectangle`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_solid_revolution_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the volume of a cylinder formed by rotating a labeled rectangle 360 degrees about a marked center line. The visible labels provide the height plus either the diameter directly or a diagonal that determines the rectangle width and cylinder diameter. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the target `V=?` cue followed by the visible diameter-or-diagonal label and height label boxes. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_revolution.py`
