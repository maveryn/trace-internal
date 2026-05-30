# `task_icons__named_field__shape_pair_arithmetic_count`

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
Evidence schema: `keyed_bbox_map` over every icon in either operand group.
Keys use `left_operand_1`, `left_operand_2`, ... and `right_operand_1`,
`right_operand_2`, ... after sorting each operand group in reading order. This
keeps operand membership explicit for difference queries where an unordered
union of boxes would be ambiguous.

## Notes
The task uses non-stack named-icon layouts and keeps the active arithmetic
operation in `query_id`.
