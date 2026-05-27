# `task_geometry__sector__sector_measure_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `sector`
4. Public query variant: `default`
5. Query id: one of `area_from_radius_and_complement_angle`, `arc_length_from_radius_and_supplement_angle`, `area_from_arc_length_and_radius`, or `arc_length_from_area_and_radius`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_sector_formula_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute a circular-sector measure through a two-step relation or cross-formula. Supported branches derive a sector angle from a complementary or supplementary relation before computing area or arc length, or derive area/arc length from the other curved measure plus radius. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over visible label boxes needed for the computation, such as the radius label plus an angle-relation label, or the radius label plus the given arc/area label.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/sector_formula.py`
