# `task_geometry__circle_pair_tangents__common_tangent_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_pair_tangents`
3. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
4. Query id: `external_common_tangent_length`
5. Answer schema: `integer_value`
6. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_external_common_tangent_measurements, unknown_role=tangent_length, formula_schema=external_common_tangent_length); scene=circle_pair_tangents; scope=common_tangent_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_pair_tangents_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed point map with visible construction-point roles `C`, `D`, `A`, and `B`, marking the two circle centers and two tangent points. Segment labels, right-angle markers, numeric labels, and the symbolic tangent formula remain visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_pair_tangents.yaml`
- Task module: `trace/tasks/geometry/circle_pair_tangents/common_tangent_length_value.py`
