# `task_geometry__circle_pair_tangents__external_tangent_segment_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_pair_tangents`
4. Query ids: `tangent_segment_length_from_center_distance`, `center_distance_from_tangent_segment_length`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_external_common_tangent_measurements, unknown_role=tangent_length|center_distance, formula_schema=external_common_tangent_right_triangle); scene=circle_pair_tangents; scope=external_tangent_segment_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_pair_tangents_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed point map with visible construction-point roles `C`, `D`, `A`, and `B`, marking the two circle centers and two tangent points. Segment labels, right-angle markers, numeric labels, and the symbolic tangent relation remain visible annotations plus private verifier metadata.

Scalar annotation does not apply because the task always needs multiple role-bound construction points.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_pair_tangents.yaml`
- Task module: `trace/tasks/geometry/circle_pair_tangents/external_tangent_segment_length_value.py`
