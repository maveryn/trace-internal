# `task_geometry__composite_shape__curvilinear_sector_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query id: `default`
5. Query id: one of `sector_angle_from_arc_length` or `sector_angle_from_area`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_curvilinear_composite_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a circular sector's central angle from the shown radius plus either arc length or sector area. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set`: the unknown angle cue first, followed by the radius label and given arc or area label.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/curvilinear_composite.py`
