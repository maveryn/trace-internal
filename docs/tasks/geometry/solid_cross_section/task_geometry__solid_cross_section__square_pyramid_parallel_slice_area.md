# `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_cross_section`
3. Task id: `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`
4. Supported `query_id` values: `single`
5. Answer schema: `decimal_value_1dp`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task requires multiple role-bound boxes for the cross section and visible measurement labels)

## Program Contract
- `solve_formula(visible_solid_cross_section_measurements, unknown_role=area_measure, formula_schema=square_pyramid_parallel_slice_area); scene=solid_cross_section; scope=square_pyramid_parallel_slice_area`

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/solid_cross_section/geometry_solid_cross_section_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a pixel-space `bbox_map` with keys `cross_section`, `base_side_label`, `height_label`, and `slice_distance_label`. Formula values, scale factors, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_cross_section.yaml`
- Prompt bundle: `prompts/geometry/solid_cross_section/geometry_solid_cross_section_v1.json`
- Task module: `trace/tasks/geometry/solid_cross_section/square_pyramid_parallel_slice_area.py`
