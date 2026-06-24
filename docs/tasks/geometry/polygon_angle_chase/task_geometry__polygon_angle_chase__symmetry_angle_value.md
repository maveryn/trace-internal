# `task_geometry__polygon_angle_chase__symmetry_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `polygon_angle_chase`
3. Task id: `task_geometry__polygon_angle_chase__symmetry_angle_value`
4. Query id: `rectangle_diagonal_angle`, `reflection_axis_angle`, or `isosceles_base_angle_chain`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; every instance requires multiple labeled point witnesses)

## Program Contract
- `derive_geometry_metric(visible_symmetry_angle_measurements, derivation_rule=symmetry_equal_angle_relations, output_role=angle_measure); scene=polygon_angle_chase; scope=symmetry_angle_value; query_args={construction: rectangle_diagonal|reflection_axis|isosceles_triangle}`

## Query Semantics
- `rectangle_diagonal_angle` asks for the complementary angle at a rectangle corner split by a diagonal.
- `reflection_axis_angle` asks for the angle between reflected rays using the visible angle to the symmetry axis.
- `isosceles_base_angle_chain` asks for either a base or apex angle in an isosceles triangle; the target role is internal replay metadata.
- Support angle values, target role, layout, and style are internal replay metadata unless explicitly supplied for testing.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a `point_map` keyed by the visible point labels in the image, such as `A`, `B`, `C`, `D` or `P`, `Q`, `R`. Each value is the pixel point at that labeled construction point. Visible degree labels, right-angle marks, equal-side ticks, and symmetry-axis marks are solver inputs, not annotation keys.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/polygon_angle_chase.yaml`
- Prompt bundle: `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`
- Task module: `trace/tasks/geometry/polygon_angle_chase/symmetry_angle_value.py`
