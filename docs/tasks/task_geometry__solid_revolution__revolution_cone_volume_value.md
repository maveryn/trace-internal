# `task_geometry__solid_revolution__revolution_cone_volume_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_revolution`
4. Public query id: `default`
5. Query id: `cone_volume_from_right_triangle`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_solid_revolution_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the volume of a cone formed by rotating a labeled right triangle 360 degrees about one leg. The visible height and slant-height labels determine the missing radius by the Pythagorean relation before applying the cone-volume formula. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the target `V=?` cue followed by the visible slant-height and height label boxes. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_revolution.py`
