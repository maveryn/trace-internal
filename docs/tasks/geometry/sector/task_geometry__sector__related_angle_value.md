# `task_geometry__sector__related_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Task id: `task_geometry__sector__related_angle_value`
4. Supported `query_id` values: `complement_angle_from_arc_length`, `supplement_angle_from_area`, `remaining_angle_from_sector_measure`
5. Answer schema: `number`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple heterogeneous sector witnesses)

## Program Contract
- `solve_formula(circular_sector, target=related_angle, formula_schema=derive_sector_angle_then_complement_supplement_or_remainder); scene=sector; scope=related_angle_value`

## Query Semantics
- `complement_angle_from_arc_length` asks for the angle complementary to a sector angle derived from arc length.
- `supplement_angle_from_area` asks for the angle supplementary to a sector angle derived from sector area.
- `remaining_angle_from_sector_measure` asks for the rest-of-circle angle after deriving the sector angle from arc length.
- Radius, angle support, style, font, layout jitter, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/sector/geometry_sector_formula_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map keys for the target related-angle cue and the visible measurement/relation readouts needed for the selected branch.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Prompt bundle: `prompts/geometry/sector/geometry_sector_formula_v1.json`
- Task module: `trace/tasks/geometry/sector/related_angle_value.py`
