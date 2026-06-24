# `task_geometry__regular_polygon_decomposition__central_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Task id: `task_geometry__regular_polygon_decomposition__central_angle_value`
4. Supported `query_id` values: `single_wedge_central_angle`, `marked_wedges_central_angle`
5. Answer schema: `integer`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds center and two angle-ray endpoint roles)

## Program Contract
- `solve_formula(regular_polygon_equal_wedge_decomposition, target=central_angle_or_adjacent_angle_span, formula_schema=360_degrees_divided_by_side_count); scene=regular_polygon_decomposition; scope=central_angle_value`

## Query Semantics
- `single_wedge_central_angle` asks for one center wedge angle of a regular polygon.
- `marked_wedges_central_angle` asks for the angle spanned by adjacent marked wedges.
- The number of polygon sides, selected wedge start, style, font, layout jitter, and rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point map keys `O`, `A`, and `B`, marking the polygon center and the two visible rays that bound the requested center angle. Angle arcs and `?` markers remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/regular_polygon_decomposition.yaml`
- Prompt bundle: `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`
- Task module: `trace/tasks/geometry/regular_polygon_decomposition/central_angle_value.py`
