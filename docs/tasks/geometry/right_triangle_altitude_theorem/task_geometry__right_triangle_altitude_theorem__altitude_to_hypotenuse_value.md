# `task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value`

## Contract
1. Domain: `geometry`
2. Scene id: `right_triangle_altitude_theorem`
3. Task id: `task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value`
4. Supported `query_id` values: `altitude_from_split_hypotenuse`, `missing_projection_from_altitude`
5. Answer schema: `integer`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds the four labeled construction points)

## Program Contract
- `solve_formula(right_triangle_altitude_to_hypotenuse, target=altitude_or_projection_length, formula_schema=altitude_geometric_mean); scene=right_triangle_altitude_theorem; scope=altitude_to_hypotenuse_value`

## Query Semantics
- `altitude_from_split_hypotenuse` asks for the altitude length from the two visible hypotenuse projections.
- `missing_projection_from_altitude` asks for one hypotenuse projection from the altitude and the other projection.
- Side orientation, style, font, layout jitter, and whole-scene rotation are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/right_triangle_altitude_theorem/geometry_right_triangle_altitude_theorem_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space point map keys `A`, `B`, `C`, and `D`, marking the visible labeled right-angle vertex, hypotenuse endpoints, and altitude foot.

Numeric labels, vertex labels, right-angle markers, altitude segment, and the unknown marker remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/right_triangle_altitude_theorem.yaml`
- Prompt bundle: `prompts/geometry/right_triangle_altitude_theorem/geometry_right_triangle_altitude_theorem_v1.json`
- Task module: `trace/tasks/geometry/right_triangle_altitude_theorem/altitude_to_hypotenuse_value.py`
