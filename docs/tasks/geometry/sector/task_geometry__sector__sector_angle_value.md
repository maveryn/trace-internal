# `task_geometry__sector__sector_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `sector`
3. Task id: `task_geometry__sector__sector_angle_value`
4. Supported `query_id` values: `angle_from_arc_length_and_radius`, `angle_from_area_and_radius`
5. Answer schema: `number`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple heterogeneous sector witnesses)

## Program Contract
- `solve_formula(circular_sector, target=central_angle, formula_schema=angle_from_arc_or_area); scene=sector; scope=sector_angle_value`

## Query Semantics
- `angle_from_arc_length_and_radius` asks for the central angle from a visible radius and arc length.
- `angle_from_area_and_radius` asks for the central angle from a visible radius and sector area.
- Radius, angle support, style, font, layout jitter, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/sector/geometry_sector_formula_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space bbox map keys for the target angle cue and the visible measurement readouts needed for the selected branch.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/sector.yaml`
- Prompt bundle: `prompts/geometry/sector/geometry_sector_formula_v1.json`
- Task module: `trace/tasks/geometry/sector/sector_angle_value.py`
