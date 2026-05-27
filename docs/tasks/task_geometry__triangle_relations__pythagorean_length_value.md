# `task_geometry__triangle_relations__pythagorean_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query variant: `default`
5. Query id: one of `chained_rectangle_diagonal_length` or `rectangle_triangle_shared_height_length`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a Pythagorean length from a right-triangle or rectangle-diagonal construction. One query derives a rectangle height from a smaller rectangle diagonal before finding a larger diagonal; the other derives a shared rectangle/triangle height from a rectangle diagonal before finding a triangle side.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target segment cue first, followed by supporting side labels and right-angle or composite-figure marks needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
