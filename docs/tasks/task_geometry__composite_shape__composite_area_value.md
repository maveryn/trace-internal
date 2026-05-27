# `task_geometry__composite_shape__composite_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query variant: `default`
5. Query id: one of `rectangle_minus_triangle_area` or `l_shape_area`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the area of a shaded straight-edged composite region using visible side labels and a subtraction/decomposition relation.

## Evidence
Prompt-facing evidence is a `bbox_set`: the shaded target region first, followed by the supporting dimension labels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
