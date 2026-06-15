# `task_icons__named_field__count_arithmetic`

## Identity
- domain: `icons`
- scene_id: `named_field`
- scene_id: `counting`
- module: `trace/tasks/icons/named_field/count_arithmetic.py`
- prompt bundle: `icons_counting_v0`

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
Annotation schema: `keyed_bbox_set_map` with keys `left_operand` and
`right_operand`. Each key maps to the reading-order list of icon bboxes for
that operand group. This keeps operand membership explicit for difference
queries where an unordered union of boxes would be ambiguous.

## Notes
The task uses non-stack named-icon layouts and keeps the active arithmetic
operation in `query_id`.
