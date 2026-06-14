# `task_geometry__triangle_congruence_correspondence__corresponding_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_congruence_correspondence`
5. Query id: `angle_mark_transfer`, `congruence_statement_angle_transfer`, or `overlapping_triangle_angle_transfer`
6. Answer schema: `integer`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_congruent_triangle_corresponding_angles, unknown_role=target_angle_measure, formula_schema=cpctc_angle_equality); scene=triangle_congruence_correspondence; scope=corresponding_angle_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_triangle_congruence_correspondence_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the target angle vertex/rays and the corresponding source angle vertex/rays:

- `target_angle_vertex`
- `target_angle_ray_1`
- `target_angle_ray_2`
- `source_angle_vertex`
- `source_angle_ray_1`
- `source_angle_ray_2`

Angle arcs, degree labels, labels, and congruence statements remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_congruence_correspondence.yaml`
- Task module: `trace/tasks/geometry/triangle_congruence_correspondence/corresponding_angle_value.py`
