# `task_icons__named_field__count_arithmetic`

## Identity
- domain: `icons`
- scene_id: `named_field`
- module: `trace/tasks/icons/named_field/count_arithmetic.py`
- prompt bundle: `icons_named_field_v1`

## Program Contract
`numeric.count_arithmetic(scene=named_field, scope=all_icons, operands=two_named_icon_groups, operators=sum|absolute_difference, output=integer)`

Renders one panel containing procedural named shape icons. The prompt names
two icon groups and asks either for their total count or the absolute difference
between their counts.

Query ids:
- `two_shape_total_count`
- `two_bound_color_total_count`
- `two_shape_difference_count`
- `two_bound_color_difference_count`

Answer schema: integer.
Annotation schema: `bbox_set`. The set contains one `[x0, y0, x1, y1]`
pixel bounding box for every icon counted in either operand group, sorted in
reading order. Operand-role instance ids remain in trace metadata, but the
public annotation is a homogeneous witness set because both supported
operators are symmetric over the two operand groups.

## Notes
The task uses non-stack named-icon layouts and keeps the active arithmetic
operation in `query_id`.
