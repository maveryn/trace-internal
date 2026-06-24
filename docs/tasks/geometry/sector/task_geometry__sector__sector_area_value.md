# `task_geometry__sector__sector_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Task id: `task_geometry__sector__sector_area_value`
4. Supported `query_id` values: `area_from_arc_length_and_radius`, `area_from_radius_and_complement_angle`
5. Answer schema: `number`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple heterogeneous sector witnesses)

## Program Contract
- `solve_formula(circular_sector, target=sector_area, formula_schema=area_from_arc_or_complement_angle); scene=sector; scope=sector_area_value`

## Query Semantics
- `area_from_arc_length_and_radius` asks for sector area from a visible radius and arc length.
- `area_from_radius_and_complement_angle` asks for sector area after deriving the sector angle from a complementary angle relation.
- Radius, angle support, style, font, layout jitter, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/sector/geometry_sector_formula_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map keys for the marked sector region and the visible measurement/relation readouts needed for the selected branch.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Prompt bundle: `prompts/geometry/sector/geometry_sector_formula_v1.json`
- Task module: `trace/tasks/geometry/sector/sector_area_value.py`
