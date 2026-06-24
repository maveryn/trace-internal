# `task_geometry__polygon_angle_chase__parallel_line_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `polygon_angle_chase`
3. Task id: `task_geometry__polygon_angle_chase__parallel_line_angle_value`
4. Query id: `single_transversal_chain` or `two_transversal_angle_sum`
5. Answer schema: `integer_value`
6. Annotation schema: `point_map`
7. Scalar annotation checked: `true` (not scalar-eligible; every instance requires multiple labeled point witnesses)

## Program Contract
- `derive_geometry_metric(visible_parallel_line_angle_measurements, derivation_rule=parallel_transversal_angle_relations, output_role=angle_measure); scene=polygon_angle_chase; scope=parallel_line_angle_value; query_args={construction: one_transversal_three_parallel_lines|two_transversals_two_parallel_lines}`

## Query Semantics
- `single_transversal_chain` asks for a missing angle from corresponding or supplementary angle structure on one transversal through three parallel lines.
- `two_transversal_angle_sum` asks for the angle between two transversals using the two visible support angles.
- Relation choice within `single_transversal_chain`, support angle values, layout, and style are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is a `point_map` keyed by the visible point labels in the image, typically `P`, `Q`, and `R`. Each value is the pixel point at that labeled intersection. Visible degree labels, angle arcs, and parallel marks are solver inputs, not annotation keys.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/polygon_angle_chase.yaml`
- Prompt bundle: `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v1.json`
- Task module: `trace/tasks/geometry/polygon_angle_chase/parallel_line_angle_value.py`
