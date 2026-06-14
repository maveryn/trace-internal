# `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`

## Contract
1. Domain: `geometry`
2. Scene id: `solid_cross_section`
5. Query id: `square_pyramid_parallel_slice_area`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_solid_cross_section_measurements, unknown_role=area_measure, formula_schema=square_pyramid_parallel_slice_area); scene=solid_cross_section; scope=square_pyramid_parallel_slice_area`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `solid_cross_section`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/solid_cross_section.yaml`
- Task module: `trace/tasks/geometry/solid_cross_section/square_pyramid_parallel_slice_area.py`
