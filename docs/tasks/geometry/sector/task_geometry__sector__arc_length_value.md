# `task_geometry__sector__arc_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Task id: `task_geometry__sector__arc_length_value`
4. Supported `query_id` values: `arc_length_from_area_and_radius`, `arc_length_from_radius_and_supplement_angle`
5. Answer schema: `number`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple heterogeneous sector witnesses)

## Program Contract
- `solve_formula(circular_sector, target=arc_length, formula_schema=arc_from_area_or_supplement_angle); scene=sector; scope=arc_length_value`

## Query Semantics
- `arc_length_from_area_and_radius` asks for arc length from a visible radius and sector area.
- `arc_length_from_radius_and_supplement_angle` asks for arc length after deriving the sector angle from a supplementary angle relation.
- Radius, angle support, style, font, layout jitter, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/sector/geometry_sector_formula_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map keys for the target arc and the visible measurement/relation readouts needed for the selected branch.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Prompt bundle: `prompts/geometry/sector/geometry_sector_formula_v1.json`
- Task module: `trace/tasks/geometry/sector/arc_length_value.py`
