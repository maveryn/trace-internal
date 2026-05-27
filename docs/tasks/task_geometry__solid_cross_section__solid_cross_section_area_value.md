# `task_geometry__solid_cross_section__solid_cross_section_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `solid_cross_section`
4. Public query variant: `default`
5. Query ids: `cone_parallel_slice_area`, `square_pyramid_parallel_slice_area`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_solid_cross_section_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the area of a marked cross-section made by a plane parallel to the base of a cone or square pyramid. The visible labels provide the full solid height, the distance from the apex to the slice, and either the base radius or base side. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the target `A=?` cue, one around the marked cross-section, and boxes around the visible measurement labels needed for the similarity computation. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/solid_cross_section.py`
