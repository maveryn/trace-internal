# `task_geometry__regular_polygon_decomposition__perimeter_value`

## Contract
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Task id: `task_geometry__regular_polygon_decomposition__perimeter_value`
4. Supported `query_id` values: `perimeter_from_side_length`, `perimeter_from_total_area_and_apothem`
5. Answer schema: `integer`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds polygon center, side endpoints, and sometimes apothem-foot roles)

## Program Contract
- `solve_formula(regular_polygon_equal_wedge_decomposition, target=regular_polygon_perimeter, formula_schema=side_count_times_side_length_or_two_area_over_apothem); scene=regular_polygon_decomposition; scope=perimeter_value`

## Query Semantics
- `perimeter_from_side_length` asks for regular-polygon perimeter from a visible side-length label.
- `perimeter_from_total_area_and_apothem` asks for regular-polygon perimeter from total area and apothem labels.
- The number of polygon sides, selected side, style, font, layout jitter, and rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point map keys `O`, `A`, `B`, and, when the apothem is visible, `M`. These mark the polygon center, support side endpoints, and apothem foot. Measurement labels and readout panels remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/regular_polygon_decomposition.yaml`
- Prompt bundle: `prompts/geometry/regular_polygon_decomposition/geometry_regular_polygon_decomposition_v1.json`
- Task module: `trace/tasks/geometry/regular_polygon_decomposition/perimeter_value.py`
