# `task_geometry__area_partition__total_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `area_partition`
4. Query id: `total_area_from_shaded_partition`
5. Answer type: `number`
6. Evidence type: `keyed_bbox_map`

## Prompt Bundle
- Bundle id: `geometry_area_partition_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer the total area of an outer triangle or parallelogram from a labeled
shaded partition region. Parallelogram variants use equal-area relationships
from both diagonals meeting at the center, sometimes with a marked midpoint
segment that halves one diagonal-quarter region. Triangle variants use a
median, a midsegment joining two side midpoints, or three medians meeting at a
centroid. Answers are numeric integers.

## Evidence
Prompt-facing evidence is a `keyed_bbox_map` with `outer_shape` and
`shaded_region` keys. Each value is one pixel bounding box around the
corresponding visual region. The partition marks, target cue, and numeric
shaded-area label remain visible annotations and render metadata rather than
standalone public evidence. Verifier evidence is projected from the same
generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/area_partition.py`
