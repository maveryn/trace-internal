# `task_geometry__composite_shape__curvilinear_composite_perimeter_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `composite_shape`
4. Public query variant: `default`
5. Query id: one of `rectangle_semicircle_cap_perimeter`, `rectangle_semicircle_cutout_perimeter`, or `rectangle_quarter_sector_cutout_perimeter`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_curvilinear_composite_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the perimeter of a shaded curvilinear composite boundary, including the relevant semicircle arc or quarter-circle arc. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over the visible straight-boundary and arc label boxes needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/curvilinear_composite.py`
