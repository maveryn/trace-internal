# `task_geometry__pythagorean_dissection__pythagorean_square_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `pythagorean_dissection`
4. Public query id: `default`
5. Query id: `central_square_area_from_triangle_legs`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_pythagorean_square_dissection_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute the area of the central tilted square in an outer square dissection. The visible labels give the outer square side length and the two legs of each congruent corner right triangle; the central square area is obtained by subtracting the four corner-triangle areas from the outer square area, equivalently by applying the Pythagorean area relation to the two labeled legs. Answers are rounded to one decimal place.
The labeled side and leg positions are sampled across mirrored placements so the evidence does not occupy a fixed image location.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the visible outer-square side label and one pixel bounding box around each visible corner-triangle leg label. It excludes the unknown central-square label and right-angle marks. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, query ids, prompt bundle ids, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/pythagorean_square_dissection.py`
