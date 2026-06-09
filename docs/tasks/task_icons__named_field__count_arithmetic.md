# `task_icons__named_field__count_arithmetic`

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- module: `trace/tasks/icons/counting/named_shape_pair_arithmetic_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders one Scene panel containing procedural named shape icons. The prompt names
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
