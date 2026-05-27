# `task_geometry__tangent_packing__tangent_packing_shaded_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `tangent_packing`
4. Public query variant: `default`
5. Query ids: `circle_in_square_gap_area`, `square_in_circle_gap_area`, `two_circles_in_rectangle_gap_area`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_circle_square_tangent_packing_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the shaded gap area in a circle/square/rectangle tangency diagram.
Query variants cover a circle inscribed in a square, a square inscribed in a
circle, and two equal tangent circles packed inside a rectangle. Answers use
the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the
target shaded-area cue, followed by the shaded tangent-packing diagram and the
visible supporting label boxes. Verifier evidence is projected from the same
generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/circle_square_tangent_packing.py`
