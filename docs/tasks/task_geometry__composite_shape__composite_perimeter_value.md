# `task_geometry__composite_shape__composite_perimeter_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query id: `default`
5. Query id: one of `house_outline_perimeter` or `tabbed_rectilinear_perimeter`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the outer perimeter of a straight-edged composite figure from visible dimensions and implied equal/opposite sides.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target boundary first, followed by supporting dimension labels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
