# `task_geometry__solid_revolution__revolution_frustum_volume_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_revolution`
4. Public query id: `default`
5. Query id: `frustum_volume_from_trapezoid`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_solid_revolution_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the volume of a frustum formed by rotating a right trapezoid 360 degrees about its marked side. The two horizontal distances from the axis give the top and bottom radii, and the marked side gives the height. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the target `V=?` cue followed by the visible top-radius, bottom-radius, and height label boxes. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_revolution.py`
