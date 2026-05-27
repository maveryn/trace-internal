# `task_geometry__incircle_tangents__incircle_tangent_perimeter_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `incircle_tangents`
4. Public query id: `default`
5. Query id: `triangle_perimeter_from_tangent_segments`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_tangent_polygon_incircle_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute the perimeter of triangle `ABC` from equal tangent-segment labels from each vertex to the incircle tangency points. Answers are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around each visible tangent-segment equality label needed to compute the perimeter. It excludes point labels, decorative tick marks, and the unknown perimeter cue. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, query ids, prompt bundle ids, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/tangent_polygon_incircle.py`
