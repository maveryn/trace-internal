# `task_geometry__triangle_congruence_correspondence__corresponding_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `triangle_congruence_correspondence`
3. Task id: `task_geometry__triangle_congruence_correspondence__corresponding_angle_value`
4. Supported `query_id` values: `angle_mark_transfer`, `congruence_statement_angle_transfer`, `overlapping_triangle_angle_transfer`
5. Answer schema: `integer`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple labeled point witnesses)

## Program Contract
- `solve_formula(visible_congruent_triangle_corresponding_angles, unknown_role=target_angle_measure, formula_schema=cpctc_angle_equality); scene=triangle_congruence_correspondence; scope=corresponding_angle_value`

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/triangle_congruence_correspondence/geometry_triangle_congruence_correspondence_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a role-bound pixel point map keyed by the visible point labels needed for the target angle and the corresponding source angle.

The visible keys vary with the sampled triangle correspondence, but they are always direct point labels such as `A`, `B`, `C`, and `D`; each value is the pixel point at that labeled vertex. Angle arcs, degree labels, and congruence statements remain visible support plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/triangle_congruence_correspondence.yaml`
- Prompt bundle: `prompts/geometry/triangle_congruence_correspondence/geometry_triangle_congruence_correspondence_v1.json`
- Task module: `trace/tasks/geometry/triangle_congruence_correspondence/corresponding_angle_value.py`
