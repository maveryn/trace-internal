# `task_geometry__regular_polygon_decomposition__piece_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Task id: `task_geometry__regular_polygon_decomposition__piece_area_value`
4. Supported `query_id` values: `single_wedge_area_from_total`, `shaded_wedges_area_from_total`, `wedge_area_from_side_and_apothem`
5. Answer schema: `number`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds center and target wedge boundary vertex roles)

## Program Contract
- `solve_formula(regular_polygon_equal_wedge_decomposition, target=wedge_or_adjacent_wedge_group_area, formula_schema=area_from_total_area_or_side_apothem); scene=regular_polygon_decomposition; scope=piece_area_value`

## Query Semantics
- `single_wedge_area_from_total` asks for one shaded wedge area from the total area of an equal-wedge regular polygon.
- `shaded_wedges_area_from_total` asks for an adjacent shaded wedge-group area from the total area of an equal-wedge regular polygon.
- `wedge_area_from_side_and_apothem` asks for a shaded triangular wedge area from its visible side length and apothem.
- The number of polygon sides, selected wedge start, style, font, layout jitter, and rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point map keys `O`, `A`, and `B`, marking the polygon center and the two visible rays that bound the requested shaded wedge or wedge group. Measurement labels and readout panels remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/regular_polygon_decomposition.yaml`
- Prompt bundle: `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`
- Task module: `trace/tasks/geometry/regular_polygon_decomposition/piece_area_value.py`
