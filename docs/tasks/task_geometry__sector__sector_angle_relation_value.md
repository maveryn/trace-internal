# `task_geometry__sector__sector_angle_relation_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `sector`
4. Public query variant: `default`
5. Query id: one of `angle_from_arc_length_and_radius`, `angle_from_area_and_radius`, `complement_angle_from_arc_length`, `supplement_angle_from_area`, or `remaining_angle_from_sector_measure`
6. Answer type: `number`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_sector_formula_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a circular sector's central angle from arc length or area, optionally then apply a complementary, supplementary, or remaining-circle angle relation. Answers use the internal pi value and are rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `bbox_set` over visible label boxes needed for the computation: the marked angle cue, radius label, arc or area label, and relation label when present.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/sector_formula.py`
