# `task_geometry__polygon_angle_chase__polygon_interior_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `polygon_angle_chase`
3. Task id: `task_geometry__polygon_angle_chase__polygon_interior_angle_value`
4. Query id: `triangle_interior_angle`, `quadrilateral_interior_angle`, `pentagon_interior_angle`, or `hexagon_interior_angle`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; every instance requires multiple labeled point witnesses)

## Program Contract
- `derive_geometry_metric(visible_polygon_angle_measurements, derivation_rule=polygon_interior_angle_sum, output_role=angle_measure); scene=polygon_angle_chase; scope=polygon_interior_angle_value; query_args={side_count: 3|4|5|6}`

## Query Semantics
- Query ids select the polygon side count only.
- Label style, target vertex, constants, angle values, layout, style, and rotation are internal replay metadata, not public query branches.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a `point_map` keyed by the visible point labels in the image, such as `A`, `B`, `C`, `D`, `E`, and `F`. Each value is the pixel point at that labeled polygon vertex. Visible angle labels and algebraic expressions are solver inputs, not annotation keys.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/polygon_angle_chase.yaml`
- Prompt bundle: `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`
- Task module: `trace/tasks/geometry/polygon_angle_chase/polygon_interior_angle_value.py`
