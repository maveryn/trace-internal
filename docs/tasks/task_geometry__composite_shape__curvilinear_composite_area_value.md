# `task_geometry__composite_shape__curvilinear_composite_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query id: `default`
5. Query id: one of `rectangle_semicircle_cap_area`, `rectangle_semicircle_cutout_area`, or `rectangle_quarter_sector_cutout_area`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_curvilinear_composite_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the area of a shaded composite shape by combining a rectangle with a semicircle or subtracting a semicircle/quarter-sector cutout. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over the visible measurement label boxes needed for the computation, such as width, height, radius, and angle labels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/curvilinear_composite.py`
