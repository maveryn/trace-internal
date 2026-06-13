# `task_geometry__circle_centerline_overlap__segment_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_centerline_overlap`
3. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
4. Query id: `center_distance_from_overlap` or `boundary_segment_from_overlap`
5. Answer schema: `integer_value`
6. Annotation schema: `keyed_point_map`

## Program Contract
- `solve_formula(visible_collinear_circle_overlap_measurements, unknown_role=target_centerline_segment, formula_schema=circle_centerline_overlap_segment_length); scene=circle_centerline_overlap; scope=segment_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_circle_centerline_overlap_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the endpoints of the requested segment only. Keys are the visible point labels in the diagram, not generic endpoint roles. For example, `AC` asks for `A` and `C`, while `AY` asks for `A` and `Y`. Numeric labels, point labels, radius/diameter readouts, and known segments remain visible context plus private verifier metadata.

## Sampling
Default generation samples circle radii and adjacent overlap lengths from deterministic constrained integer ranges instead of a small fixed case bank. The constraints preserve proper adjacent circle overlaps, keep non-adjacent circles separated, and ensure boundary-segment answers remain at least 3.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_centerline_overlap.yaml`
- Task module: `trace/tasks/geometry/circle_centerline_overlap/segment_length_value.py`
