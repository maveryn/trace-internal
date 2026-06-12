# `task_geometry__circle_centerline_overlap__segment_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_centerline_overlap`
3. Scene id: `circle_centerline_overlap`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `center_distance_from_overlap` or `boundary_segment_from_overlap`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_collinear_circle_overlap_measurements, unknown_role=target_centerline_segment, formula_schema=circle_centerline_overlap_segment_length); scene=circle_centerline_overlap; scope=segment_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_centerline_overlap_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the minimal visible witnesses. For `center_distance_from_overlap`, annotation marks the three centers and the two adjacent overlap segments. For `boundary_segment_from_overlap`, annotation marks the target segment endpoints, known segment endpoints, and the three circle centers. Numeric labels, point labels, and radius/diameter readouts remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_centerline_overlap.yaml`
- Task module: `trace/tasks/geometry/circle_centerline_overlap/segment_length_value.py`
