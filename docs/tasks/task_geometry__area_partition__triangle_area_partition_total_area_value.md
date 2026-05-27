# `task_geometry__area_partition__triangle_area_partition_total_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `area_partition`
4. Public query variant: `default`
5. Query id: `total_area_from_shaded_partition`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_area_partition_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer the total area of a triangle from a labeled shaded partition region. The
scene uses equal-area relationships from a median, a midsegment joining two
side midpoints, or three medians meeting at a centroid. Answers are numeric
integers.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the
target total-area cue, followed by the shaded region, the shaded-area label,
and the visible partition marks. Verifier evidence is projected from the same
generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/area_partition.py`
