# `task_geometry__polygon_equation_diagram__perimeter_constraint_variable_value`

## Contract
1. Domain: `geometry`
2. Scene id: `polygon_equation_diagram`
3. Supported `query_id`: `single`
4. Answer schema: `integer`
5. Annotation schema: `point_map`

## Program Contract
- `solve_formula(visible_perimeter_constraint_side_expression_sum, unknown_role=variable_value, formula_schema=perimeter_constraint_variable_value); scene=polygon_equation_diagram; scope=perimeter_constraint_variable_value`

## Internal Construction Families
The public task has no semantic query branch. The sampled polygon side count is recorded as trace metadata:

- `triangle`
- `quadrilateral`
- `pentagon`
- `hexagon`

## Prompt Bundle
- Prompt text is loaded from `geometry_polygon_equation_diagram_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a `point_map` keyed by the visible polygon vertex labels, such as `A`, `B`, `C`, and any additional visible vertices. Each value is that labeled vertex's pixel coordinate after final layout and rotation.

The diagram shows side labels plus a visible total perimeter label. The answer is the variable value that
makes the sum of visible side expressions equal the displayed perimeter.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/polygon_equation_diagram.yaml`
- Task module: `trace/tasks/geometry/polygon_equation_diagram/perimeter_constraint_variable_value.py`
