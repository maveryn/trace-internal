# `task_geometry__composite_shape__curvilinear_missing_side_from_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query id: `default`
5. Query id: one of `missing_width_from_semicircle_cap_area` or `missing_width_from_semicircle_cutout_area`
6. Answer type: `number`
7. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_curvilinear_composite_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer the missing rectangle width from the total area of a rectangle-plus-semicircle or rectangle-minus-semicircle composite. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over the two visible endpoints of the unknown side. Total area, height, and radius labels remain visible annotations and render metadata, not public evidence.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/curvilinear_composite.py`
