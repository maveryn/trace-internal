# `task_geometry__polygon_angle_chase__polygon_interior_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `polygon_angle_chase`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `triangle_interior_angle`, `quadrilateral_interior_angle`, `pentagon_interior_angle`, or `hexagon_interior_angle`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_polygon_angle_measurements, derivation_rule=polygon_interior_angle_sum, output_role=angle_measure); scene=polygon_angle_chase; scope=polygon_interior_angle_value`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points at the target angle vertex and each visible supporting angle vertex. Visible angle labels and algebraic expressions are annotations used by the solver, not the annotation object itself.

## Label Styles
1. `target_expression_mixed`: the requested angle and one or two support angles are labeled as linear expressions in `x`, with the remaining support angles numeric.
2. `all_expression`: every interior angle is labeled as a linear expression in `x`.
3. The answer is always the evaluated requested angle measure, not the value of `x`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_polygon_angle_chase_v0.json`
- Task module: `trace/tasks/geometry/measurement/polygon_angle_chase.py`
